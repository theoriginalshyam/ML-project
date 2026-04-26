import json
import warnings
from datetime import date
from pathlib import Path

import gymnasium as gym
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yfinance as yf
from gymnasium import spaces
from hmmlearn.hmm import GaussianHMM
from sb3_contrib import CrossQ, RecurrentPPO, TQC
from sklearn.preprocessing import StandardScaler
from stable_baselines3 import TD3
from stable_baselines3.common.vec_env import DummyVecEnv

warnings.filterwarnings("ignore")


class RuntimeConfigurationError(RuntimeError):
    pass


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

BASE_DIR = Path(__file__).parent / "output"
AGENTS_DIR = BASE_DIR / "agents"
GATING_DATA_FILE = BASE_DIR / "gating_dataset.json"
GATING_MODEL_FILE = BASE_DIR / "gating_net.pt"
SENTIMENT_CACHE_FILE = BASE_DIR / "sentiment_cache.parquet"
STATE_FILE = BASE_DIR / "state.json"

TICKERS = [
    "AAPL",
    "MSFT",
    "JPM",
    "JNJ",
    "V",
    "PG",
    "UNH",
    "HD",
    "MA",
    "INTC",
    "VZ",
    "MRK",
    "DIS",
    "BA",
    "MMM",
    "IBM",
    "AXP",
    "GS",
    "CAT",
    "MCD",
    "NKE",
    "WMT",
    "TRV",
    "CVX",
    "RTX",
    "DOW",
    "AMGN",
    "HON",
    "CRM",
    "KO",
]

TRAIN_START = "2012-01-01"
VAL_START = "2024-01-01"
VAL_END = "2024-12-31"
TRADE_START = "2025-01-01"

INITIAL_CAPITAL = 1_000_000
TRANSACTION_COST = 0.001
HMAX = 100
TARGET_STOCK_VOL = 0.02
MIN_VOL_HMAX = 10
MAX_VOL_HMAX = 500
TURB_MIDPOINT = 150
TURB_STEEPNESS = 50
TURB_FLOOR = 0.05
DD_THRESHOLD = 0.05
N_REGIMES = 4
REGIME_WINDOW = 20
REGIME_NAMES = ["bull_low_vol", "bull_high_vol", "bear_low_vol", "bear_high_vol"]
AGENT_NAMES = ["TQC", "CrossQ", "TD3", "RPPO"]
N_AGENTS = len(AGENT_NAMES)
GATING_INPUT_DIM = N_REGIMES + N_AGENTS + 3
MIN_GATING_SAMPLES = 4
N_ENVS = 1
SHARPE_EVAL_DAYS = 21

_FINBERT_PIPE = None
_RUNTIME_CACHE = None


def _iso(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _month_label(ts):
    t = pd.Timestamp(ts)
    return f"{t.year}-{t.month:02d}"


def _norm_ts(ts):
    t = pd.Timestamp(ts)
    if t.tzinfo is not None:
        t = t.tz_localize(None)
    return t.normalize()


def _as_float_dict(keys, values):
    return {str(k): float(v) for k, v in zip(keys, values)}


def ensure_output_dir():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)


def required_agent_paths():
    return [AGENTS_DIR / f"{name}.zip" for name in AGENT_NAMES]


def ensure_agent_artifacts():
    missing = [path.name for path in required_agent_paths() if not path.exists()]
    if missing:
        raise RuntimeConfigurationError(
            "Missing trained agent artifacts in ML_Models/output/agents: "
            + ", ".join(missing)
        )


def ensure_state_file():
    if not STATE_FILE.exists():
        raise RuntimeConfigurationError(
            "Missing ML_Models/output/state.json. Run bootstrap_state.py after copying trained artifacts."
        )


def get_finbert():
    global _FINBERT_PIPE
    if _FINBERT_PIPE is not None:
        return None if _FINBERT_PIPE == "unavailable" else _FINBERT_PIPE
    try:
        from transformers import pipeline as hf_pipeline

        dev = 0 if torch.cuda.is_available() else -1
        _FINBERT_PIPE = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            device=dev,
            truncation=True,
            max_length=512,
            batch_size=32,
        )
    except Exception:
        _FINBERT_PIPE = "unavailable"
    return None if _FINBERT_PIPE == "unavailable" else _FINBERT_PIPE


def vix_to_sentiment(vix_val):
    return float(
        np.clip(-(2.0 / (1.0 + np.exp(-(vix_val - 20.0) / 8.0)) - 1.0), -1.0, 1.0)
    )


def _fetch_ticker_news(ticker_str):
    try:
        items = []
        for news in yf.Ticker(ticker_str).news or []:
            title = news.get("title", news.get("headline", ""))
            ts = news.get("providerPublishTime", news.get("published", 0))
            if isinstance(ts, str):
                try:
                    ts = int(pd.Timestamp(ts).timestamp())
                except Exception:
                    ts = 0
            if title and ts:
                items.append((str(title), int(ts)))
        return items
    except Exception:
        return []


def _score_batch(pipe, texts):
    results = pipe(texts, truncation=True, max_length=512)
    scored = []
    for result in results:
        label = result["label"]
        conf = result["score"]
        if label == "positive":
            scored.append(conf)
        elif label == "negative":
            scored.append(-conf)
        else:
            scored.append(0.0)
    return scored


def build_sentiment_series(tickers, all_dates, vix_series):
    ensure_output_dir()
    if SENTIMENT_CACHE_FILE.exists():
        cached_df = pd.read_parquet(SENTIMENT_CACHE_FILE)
        cached_df["date"] = pd.to_datetime(cached_df["date"]).apply(_norm_ts)
    else:
        cached_df = pd.DataFrame(columns=["date", "sentiment"])

    cached_dates = set(cached_df["date"].tolist())
    pipe = get_finbert()
    if pipe is not None:
        all_items = []
        for ticker in tickers:
            for title, ts in _fetch_ticker_news(ticker):
                d = _norm_ts(pd.Timestamp(ts, unit="s"))
                if d not in cached_dates:
                    all_items.append((d, title))
        if all_items:
            dates_list = [item[0] for item in all_items]
            texts = [item[1] for item in all_items]
            try:
                scores = _score_batch(pipe, texts)
                new_df = pd.DataFrame({"date": dates_list, "sentiment": scores})
                new_df = new_df.groupby("date")["sentiment"].mean().reset_index()
                cached_df = (
                    pd.concat([cached_df, new_df], ignore_index=True)
                    .drop_duplicates("date")
                    .sort_values("date")
                    .reset_index(drop=True)
                )
                cached_df.to_parquet(SENTIMENT_CACHE_FILE)
            except Exception:
                pass

    date_to_score = dict(zip(cached_df["date"], cached_df["sentiment"])) if not cached_df.empty else {}
    vix_dict = {}
    if isinstance(vix_series, pd.Series):
        for k, v in vix_series.items():
            if not (isinstance(v, float) and np.isnan(v)):
                vix_dict[_norm_ts(k)] = float(v)

    result = []
    for d in all_dates:
        dt = _norm_ts(d)
        if dt in date_to_score:
            result.append(float(date_to_score[dt]))
        else:
            result.append(vix_to_sentiment(vix_dict.get(dt, 20.0)))
    return np.array(result, dtype=np.float32)


def download_data(tickers, start, end):
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeConfigurationError("Unable to download market data for ensemble runtime.")
    close = raw["Close"].ffill().dropna(axis=1, how="all")
    high = raw["High"].ffill()
    low = raw["Low"].ffill()
    volume = raw["Volume"].ffill().fillna(0)
    available = close.columns.tolist()
    close, high, low, volume = close[available], high[available], low[available], volume[available]

    frames = []
    for ticker in available:
        c, h, l, v = close[ticker], high[ticker], low[ticker], volume[ticker]
        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        diff = c.diff()
        rsi = 100 - 100 / (
            1
            + diff.clip(lower=0).rolling(14).mean()
            / (-diff.clip(upper=0).rolling(14).mean() + 1e-9)
        )
        tp = (h + l + c) / 3
        cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std() + 1e-9)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        adx = (tr.rolling(14).mean() / (c + 1e-9) * 100).rolling(14).mean()
        bb_pos = (c - c.rolling(20).mean()) / (2 * c.rolling(20).std() + 1e-9)
        vol_ratio = v / (v.rolling(20).mean() + 1e-9)
        frames.append(
            pd.DataFrame(
                {
                    "date": c.index,
                    "ticker": ticker,
                    "close": c.values,
                    "macd": macd.values,
                    "rsi": rsi.values,
                    "cci": cci.values,
                    "adx": adx.values,
                    "bb_pos": bb_pos.values,
                    "vol_ratio": vol_ratio.values,
                }
            )
        )
    return pd.concat(frames, ignore_index=True).dropna()


def download_macro(start, end):
    def _get_close(symbol):
        try:
            raw = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            if raw.empty:
                return pd.Series(dtype=float)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.droplevel(1)
            series = raw["Close"].ffill().bfill()
            series.index = pd.to_datetime(series.index)
            return series
        except Exception:
            return pd.Series(dtype=float)

    return _get_close("^VIX"), _get_close("^TNX")


def compute_turbulence(price_df):
    returns = price_df.pct_change().dropna()
    mu = returns.mean().values
    cov_inv = np.linalg.pinv(returns.cov().values)
    centered = returns.values - mu
    scores = np.einsum("ti,ij,tj->t", centered, cov_inv, centered)
    series = pd.Series(scores, index=returns.index)
    mn, mx = series.min(), series.max()
    return (series - mn) / (mx - mn) * 400 if mx > mn else series


def compute_turbulence_forecast(turb):
    vals = turb.values.astype(np.float64)
    mu = vals.mean()
    y, x = vals[1:] - mu, vals[:-1] - mu
    phi = float(np.dot(x, y) / (np.dot(x, x) + 1e-9))
    phi = np.clip(phi, -0.99, 0.99)
    fcast = np.clip(mu + phi * (vals - mu), 0, 400)
    return pd.Series(fcast, index=turb.index)


def turb_scale(turb_value):
    raw = 1.0 / (1.0 + np.exp((turb_value - TURB_MIDPOINT) / TURB_STEEPNESS))
    return float(max(TURB_FLOOR, raw))


def fit_regime_hmm(price_df):
    try:
        port_ret = price_df.pct_change().dropna().mean(axis=1)
        roll_mu = port_ret.rolling(REGIME_WINDOW).mean().dropna()
        roll_vol = port_ret.rolling(REGIME_WINDOW).std().dropna()
        idx = roll_mu.index.intersection(roll_vol.index)
        X = np.column_stack([roll_mu.loc[idx].values, roll_vol.loc[idx].values])
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = GaussianHMM(
            n_components=N_REGIMES,
            covariance_type="diag",
            n_iter=500,
            random_state=42,
            min_covar=1e-3,
        )
        model.fit(X_scaled)
        return model, idx, scaler
    except Exception:
        return None


def label_regimes(model_tuple, price_df):
    if model_tuple is None:
        return pd.Series(dtype=str)
    hmm, idx, scaler = model_tuple
    port_ret = price_df.pct_change().dropna().mean(axis=1)
    roll_mu = port_ret.rolling(REGIME_WINDOW).mean().dropna()
    roll_vol = port_ret.rolling(REGIME_WINDOW).std().dropna()
    common = roll_mu.index.intersection(roll_vol.index)
    X = np.column_stack([roll_mu.loc[common].values, roll_vol.loc[common].values])
    raw = hmm.predict(scaler.transform(X))
    state_mu = np.array([X[raw == s, 0].mean() if (raw == s).any() else 0 for s in range(N_REGIMES)])
    state_vol = np.array([X[raw == s, 1].mean() if (raw == s).any() else 0 for s in range(N_REGIMES)])
    med_vol = np.median(state_vol)
    state_to_regime = {}
    for s in range(N_REGIMES):
        bull = state_mu[s] >= 0
        high_vol = state_vol[s] >= med_vol
        state_to_regime[s] = (
            "bull_high_vol"
            if bull and high_vol
            else "bull_low_vol"
            if bull
            else "bear_high_vol"
            if high_vol
            else "bear_low_vol"
        )
    return pd.Series([state_to_regime[s] for s in raw], index=common)


def get_current_regime(regime_series, date_idx):
    if regime_series.empty:
        return "unknown"
    available = regime_series.index[regime_series.index <= date_idx]
    if len(available) == 0:
        return "unknown"
    val = regime_series.loc[available[-1]]
    return str(val if not isinstance(val, pd.Series) else val.iloc[-1])


class GatingNet(nn.Module):
    def __init__(self, input_dim=GATING_INPUT_DIM, hidden=32, n_agents=N_AGENTS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.BatchNorm1d(hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden, 16),
            nn.ReLU(),
            nn.Linear(16, n_agents),
        )

    def forward(self, x):
        return self.net(x)

    def predict(self, regime, sharpes, vix_val=20.0, sentiment_val=0.0, yield_val=3.0):
        feat = _gating_features(regime, sharpes, vix_val, sentiment_val, yield_val)
        x = torch.tensor(feat, dtype=torch.float32).unsqueeze(0)
        self.eval()
        with torch.no_grad():
            idx = int(self.forward(x).argmax(dim=1).item())
        return AGENT_NAMES[idx]


def _gating_features(regime, sharpes, vix_val=20.0, sentiment_val=0.0, yield_val=3.0):
    one_hot = np.zeros(N_REGIMES, dtype=np.float32)
    if regime in REGIME_NAMES:
        one_hot[REGIME_NAMES.index(regime)] = 1.0
    sv = np.array([sharpes.get(name, 0.0) for name in AGENT_NAMES], dtype=np.float32)
    s_min, s_max = sv.min(), sv.max()
    if s_max > s_min:
        sv = (sv - s_min) / (s_max - s_min) * 2.0 - 1.0
    macro = np.array([float(vix_val) / 100.0, float(sentiment_val), float(yield_val) / 10.0], dtype=np.float32)
    return np.concatenate([one_hot, sv, macro])


def load_gating_dataset():
    if GATING_DATA_FILE.exists():
        with open(GATING_DATA_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return []


REGIME_PRIOR = {
    "bull_low_vol": ["TD3", "TQC", "RPPO", "CrossQ"],
    "bull_high_vol": ["RPPO", "TQC", "CrossQ", "TD3"],
    "bear_low_vol": ["CrossQ", "RPPO", "TQC", "TD3"],
    "bear_high_vol": ["TQC", "CrossQ", "RPPO", "TD3"],
    "unknown": ["TQC", "CrossQ", "RPPO", "TD3"],
}


def coldstart_select(regime, sharpes):
    prior_rank = REGIME_PRIOR.get(regime, REGIME_PRIOR["unknown"])
    n = len(AGENT_NAMES)
    prior_score = {a: (n - prior_rank.index(a)) / n for a in AGENT_NAMES}
    sv = np.array([sharpes.get(a, 0.0) for a in AGENT_NAMES])
    s_min, s_max = sv.min(), sv.max()
    sh_norm = (sv - s_min) / (s_max - s_min) if s_max > s_min else np.ones(n) / n
    sh_score = {a: float(sh_norm[i]) for i, a in enumerate(AGENT_NAMES)}
    combined = {a: 0.6 * prior_score[a] + 0.4 * sh_score[a] for a in AGENT_NAMES}
    return max(combined, key=combined.get)


def load_gating_net():
    if not GATING_MODEL_FILE.exists():
        return None
    net = GatingNet()
    net.load_state_dict(torch.load(GATING_MODEL_FILE, map_location="cpu"))
    return net


def select_agent(regime, sharpes, gating_net, dataset, vix_val=20.0, sentiment_val=0.0, yield_val=3.0):
    if gating_net is not None and len(dataset) >= MIN_GATING_SAMPLES:
        return gating_net.predict(regime, sharpes, vix_val, sentiment_val, yield_val)
    return coldstart_select(regime, sharpes)


class MarketArrays:
    def __init__(self, data, turbulence, turb_forecast, tickers, vix_series, tny_series, sentiment_arr):
        dates = sorted(data["date"].unique())
        self.dates = dates
        self.T = len(dates)
        self.tickers = tickers
        self.N = len(tickers)

        def _pivot(col):
            return (
                data.pivot(index="date", columns="ticker", values=col)
                .reindex(index=dates, columns=tickers)
                .ffill()
                .fillna(0.0)
                .values.astype(np.float32)
            )

        self.prices = _pivot("close")
        self.macd = _pivot("macd")
        self.rsi = _pivot("rsi")
        self.cci = _pivot("cci")
        self.adx = _pivot("adx")
        self.bb_pos = _pivot("bb_pos")
        self.vol_ratio = _pivot("vol_ratio")

        def _macro_at(series, default):
            if not isinstance(series, pd.Series) or series.empty:
                return np.full(len(dates), float(default), dtype=np.float32)
            lookup = {_norm_ts(k): float(v) for k, v in series.items() if not (isinstance(v, float) and np.isnan(v))}
            return np.array([lookup.get(_norm_ts(d), float(default)) for d in dates], dtype=np.float32)

        self.turb = _macro_at(turbulence, 0.0)
        self.turb_fcast = _macro_at(turb_forecast, 0.0)
        self.vix = _macro_at(vix_series, 20.0)
        self.yield10y = _macro_at(tny_series, 3.0)
        self.vix_change = np.concatenate([[0.0], np.diff(self.vix)]).astype(np.float32)

        if len(sentiment_arr) != self.T:
            raise ValueError(f"sentiment_arr length {len(sentiment_arr)} != T={self.T}")
        self.sentiment = sentiment_arr.astype(np.float32)
        self.vol_hmax = self._build_vol_hmax()

    def _build_vol_hmax(self):
        window = 20
        ret = np.zeros_like(self.prices)
        ret[1:] = np.diff(self.prices, axis=0) / (self.prices[:-1] + 1e-9)
        vh = np.full((self.T, self.N), float(HMAX), dtype=np.float32)
        for t in range(window, self.T):
            dv = ret[t - window : t].std(axis=0) + 1e-9
            vh[t] = np.clip(TARGET_STOCK_VOL / dv * HMAX, MIN_VOL_HMAX, MAX_VOL_HMAX).astype(np.float32)
        return vh


class StockTradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, arrays, i_start=0, i_end=None, initial_capital=None):
        super().__init__()
        self.arrays = arrays
        self.i_start = i_start
        self.i_end = i_end if i_end is not None else arrays.T
        self.T = self.i_end - self.i_start
        self.N = arrays.N
        self.capital = initial_capital if initial_capital is not None else INITIAL_CAPITAL
        obs_dim = 1 + 8 * self.N + 5
        self._buf = np.empty(obs_dim, dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, (obs_dim,), np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, (self.N,), np.float32)

    def _ai(self):
        return self.i_start + self.step_idx

    def _obs(self):
        ai = min(self._ai(), self.i_end - 1)
        buf = self._buf
        N = self.N
        if ai > 0:
            ret = (self.arrays.prices[ai] - self.arrays.prices[ai - 1]) / (self.arrays.prices[ai - 1] + 1e-9)
        else:
            ret = np.zeros(N, dtype=np.float32)

        buf[0] = self.balance / self.capital
        buf[1 : 1 + N] = ret
        buf[1 + N : 1 + 2 * N] = self.shares / HMAX
        buf[1 + 2 * N : 1 + 3 * N] = self.arrays.macd[ai] / 100.0
        buf[1 + 3 * N : 1 + 4 * N] = self.arrays.rsi[ai] / 100.0
        buf[1 + 4 * N : 1 + 5 * N] = self.arrays.cci[ai] / 200.0
        buf[1 + 5 * N : 1 + 6 * N] = self.arrays.adx[ai] / 100.0
        buf[1 + 6 * N : 1 + 7 * N] = self.arrays.bb_pos[ai]
        buf[1 + 7 * N : 1 + 8 * N] = np.clip(self.arrays.vol_ratio[ai] / 3.0, 0, 2)
        buf[1 + 8 * N] = self.arrays.turb_fcast[ai] / 400.0
        buf[1 + 8 * N + 1] = self.arrays.vix[ai] / 100.0
        buf[1 + 8 * N + 2] = np.clip(self.arrays.vix_change[ai] / 10.0, -1.0, 1.0)
        buf[1 + 8 * N + 3] = self.arrays.yield10y[ai] / 10.0
        buf[1 + 8 * N + 4] = self.arrays.sentiment[ai]
        return buf.copy()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_idx = 0
        self.balance = float(self.capital)
        self.shares = np.zeros(self.N, dtype=np.float64)
        self.portfolio_v = [self.capital]
        self._returns = []
        self.monthly_peak = float(self.capital)
        return self._obs(), {}

    def step(self, action):
        ai = self._ai()
        prices = self.arrays.prices[ai].astype(np.float64)
        turb_sc = turb_scale(float(self.arrays.turb[ai]))
        drawdown = (self.portfolio_v[-1] - self.monthly_peak) / (self.monthly_peak + 1e-9)
        dd_brake = float(np.clip(1.0 + drawdown / DD_THRESHOLD, 0.0, 1.0))
        scale = turb_sc * dd_brake
        vh = self.arrays.vol_hmax[ai].astype(np.float64)
        acts = (action * scale * vh).astype(np.int32)

        sell_mask = (acts < 0) & (prices > 0)
        if sell_mask.any():
            k = np.minimum(-acts[sell_mask], self.shares[sell_mask].astype(np.int32))
            self.balance += (k * prices[sell_mask] * (1.0 - TRANSACTION_COST)).sum()
            self.shares[sell_mask] -= k

        buy_mask = (acts > 0) & (prices > 0)
        if buy_mask.any():
            cost_per = prices[buy_mask] * (1.0 + TRANSACTION_COST)
            total_req = (acts[buy_mask].astype(np.float64) * cost_per).sum()
            if total_req > 0:
                sf = min(1.0, self.balance / total_req)
                k_arr = np.floor(acts[buy_mask].astype(np.float64) * sf).astype(np.int64)
                cost = (k_arr * cost_per).sum()
                if cost <= self.balance:
                    self.balance -= cost
                    self.shares[buy_mask] += k_arr

        self.step_idx += 1
        done = self.step_idx >= self.T
        next_ai = self._ai() if not done else ai
        pv = self.balance + (self.shares * self.arrays.prices[next_ai].astype(np.float64)).sum()
        self.portfolio_v.append(pv)
        if pv > self.monthly_peak:
            self.monthly_peak = pv
        raw_ret = (pv - self.portfolio_v[-2]) / self.capital
        self._returns.append(raw_ret)
        window = self._returns[-20:]
        neg = [r for r in window if r < 0]
        dv = float(np.std(neg)) if len(neg) >= 3 else float(np.std(window) + 1e-9)
        reward = raw_ret / (dv + 1e-9) - 0.001 * float(np.abs(action).mean())
        return self._obs(), float(reward), done, False, {}


def _clean(pv):
    vals = np.array(pv, dtype=float)
    return np.where(vals == 0, 1e-9, vals)


def sharpe_ratio(pv, rf=0.0):
    vals = _clean(pv)
    r = np.diff(vals) / vals[:-1]
    if len(r) == 0 or r.std() < 1e-9:
        return 0.0
    return float((r.mean() * 252 - rf) / (r.std() * np.sqrt(252)))


def sortino_ratio(pv, rf=0.0):
    vals = _clean(pv)
    r = np.diff(vals) / vals[:-1]
    neg = r[r < 0]
    if len(neg) < 2 or neg.std() < 1e-9:
        return 0.0
    return float((r.mean() * 252 - rf) / (neg.std() * np.sqrt(252)))


def compute_metrics(pv):
    if len(pv) < 2:
        return {
            "Cum.Ret": "0.0%",
            "Ann.Ret": "0.0%",
            "Ann.Vol": "0.0%",
            "Sharpe": "0.00",
            "Sortino": "0.00",
            "MaxDD": "0.0%",
        }
    vals = _clean(pv)
    r = np.diff(vals) / vals[:-1]
    cum = (vals[-1] - vals[0]) / vals[0]
    ann = (1 + cum) ** (1 / max(len(r) / 252, 0.01)) - 1
    peaks = np.maximum.accumulate(vals)
    return {
        "Cum.Ret": f"{cum * 100:.1f}%",
        "Ann.Ret": f"{ann * 100:.1f}%",
        "Ann.Vol": f"{r.std() * np.sqrt(252) * 100:.1f}%",
        "Sharpe": f"{sharpe_ratio(pv):.2f}",
        "Sortino": f"{sortino_ratio(pv):.2f}",
        "MaxDD": f"{((vals - peaks) / peaks).min() * 100:.1f}%",
    }


def _make_vec_env(arrays, i_start, i_end, n_envs=1):
    fns = [lambda s=i_start, e=i_end: StockTradingEnv(arrays, i_start=s, i_end=e) for _ in range(n_envs)]
    return DummyVecEnv(fns)


def load_agents(arrays, i_end, directory=AGENTS_DIR):
    loaders = {"TQC": TQC, "CrossQ": CrossQ, "TD3": TD3, "RPPO": RecurrentPPO}
    expected = [directory / f"{name}.zip" for name in loaders]
    if not all(path.exists() for path in expected):
        return None
    off_env = _make_vec_env(arrays, 0, i_end, n_envs=N_ENVS)
    rppo_env = _make_vec_env(arrays, 0, i_end, n_envs=1)
    envs = {"TQC": off_env, "CrossQ": off_env, "TD3": off_env, "RPPO": rppo_env}
    agents = {}
    for name, cls in loaders.items():
        agents[name] = cls.load(str(directory / name), env=envs[name], device=DEVICE)
    return agents


def validate_agent(agent, arrays, i0, i1):
    env = StockTradingEnv(arrays, i_start=i0, i_end=i1)
    obs, _ = env.reset()
    done = False
    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)
    while not done:
        if isinstance(agent, RecurrentPPO):
            act, lstm_states = agent.predict(
                obs, state=lstm_states, episode_start=episode_starts, deterministic=True
            )
            episode_starts = np.zeros((1,), dtype=bool)
        else:
            act, _ = agent.predict(obs, deterministic=True)
        obs, _, done, _, _ = env.step(act)
    return sharpe_ratio(env.portfolio_v)


def split_months(arrays, trade_dates):
    di = {d: i for i, d in enumerate(arrays.dates)}
    dti = pd.DatetimeIndex(trade_dates)
    out = []
    for period, grp in dti.to_series().groupby(dti.to_period("M")):
        chunk = pd.DatetimeIndex(grp.values)
        if len(chunk) == 0:
            continue
        label = f"{period.year}-{period.month:02d}"
        out.append((di[chunk[0]], di[chunk[-1]] + 1, label))
    return out


def _run_agent(agent, arrays, i_start, i_end, balance, shares, monthly_peak=None):
    env = StockTradingEnv(arrays, i_start=i_start, i_end=i_end, initial_capital=balance)
    obs, _ = env.reset()
    env.shares = shares.copy()
    env.balance = float(balance)
    env.portfolio_v = [float(balance + (shares * arrays.prices[i_start].astype(np.float64)).sum())]
    env.monthly_peak = float(monthly_peak if monthly_peak is not None else env.portfolio_v[-1])
    done = False
    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)
    while not done:
        if isinstance(agent, RecurrentPPO):
            act, lstm_states = agent.predict(
                obs, state=lstm_states, episode_start=episode_starts, deterministic=True
            )
            episode_starts = np.zeros((1,), dtype=bool)
        else:
            act, _ = agent.predict(obs, deterministic=True)
        obs, _, done, _, _ = env.step(act)
    return env.portfolio_v[1:], float(env.balance), env.shares.copy(), float(env.monthly_peak)


def _prepare_runtime():
    ensure_output_dir()
    ensure_agent_artifacts()
    end = (pd.Timestamp(date.today()) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    data = download_data(TICKERS, TRAIN_START, end)
    wide = data.pivot(index="date", columns="ticker", values="close").ffill()
    vix_s, tny_s = download_macro(TRAIN_START, end)
    turbulence = compute_turbulence(wide)
    turb_forecast = compute_turbulence_forecast(turbulence)
    regime_model = fit_regime_hmm(wide)
    regime_series = label_regimes(regime_model, wide) if regime_model else pd.Series(dtype=str)
    all_dates = sorted(data["date"].unique())
    tickers = sorted(data["ticker"].unique())
    sentiment_arr = build_sentiment_series(tickers, all_dates, vix_s)
    arrays = MarketArrays(data, turbulence, turb_forecast, tickers, vix_s, tny_s, sentiment_arr)
    agents = load_agents(arrays, i_end=arrays.T)
    if agents is None:
        raise RuntimeConfigurationError("Missing trained agents or unable to load saved RL artifacts.")
    val_start = pd.Timestamp(VAL_START)
    val_end = pd.Timestamp(VAL_END)
    val_i0 = min((i for i, d in enumerate(arrays.dates) if d >= val_start), default=0)
    val_i1 = max((i for i, d in enumerate(arrays.dates) if d <= val_end), default=arrays.T - 1) + 1
    return {
        "arrays": arrays,
        "agents": agents,
        "regime_series": regime_series,
        "gating_dataset": load_gating_dataset(),
        "gating_net": load_gating_net(),
        "val_i0": val_i0,
        "val_i1": val_i1,
    }


def get_runtime(force=False):
    global _RUNTIME_CACHE
    if _RUNTIME_CACHE is None or force:
        _RUNTIME_CACHE = _prepare_runtime()
    return _RUNTIME_CACHE


def read_state():
    ensure_state_file()
    with open(STATE_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def write_state(state):
    ensure_output_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    return state


def recommendation_sort_key(item):
    signal_rank = {"BUY": 0, "HOLD": 1, "SELL": 2}
    conviction_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "HOLD": 3}
    return (
        signal_rank.get(item["signal"], 3),
        conviction_rank.get(item["conviction"], 4),
        item["ticker"],
    )


def _state_shares_vector(state, arrays):
    return np.array([float(state["model_shares"].get(ticker, 0)) for ticker in arrays.tickers], dtype=np.float64)


def _portfolio_value(balance, shares, prices):
    return float(balance + (shares * prices.astype(np.float64)).sum())


def _preview_actions(raw_action, arrays, idx, balance, shares, monthly_peak, current_portfolio_value):
    prices = arrays.prices[idx].astype(np.float64)
    turb_sc = turb_scale(float(arrays.turb[idx]))
    drawdown = (current_portfolio_value - monthly_peak) / (monthly_peak + 1e-9)
    dd_brake = float(np.clip(1.0 + drawdown / DD_THRESHOLD, 0.0, 1.0))
    scale = turb_sc * dd_brake
    vh = arrays.vol_hmax[idx].astype(np.float64)
    proposed = (raw_action * scale * vh).astype(np.int32)
    adjusted = proposed.copy()

    sell_mask = adjusted < 0
    if sell_mask.any():
        adjusted[sell_mask] = -np.minimum(-adjusted[sell_mask], shares[sell_mask].astype(np.int32))

    buy_mask = adjusted > 0
    if buy_mask.any():
        cost_per = prices[buy_mask] * (1.0 + TRANSACTION_COST)
        total_req = (adjusted[buy_mask].astype(np.float64) * cost_per).sum()
        if total_req > 0:
            scale_factor = min(1.0, balance / total_req)
            adjusted[buy_mask] = np.floor(adjusted[buy_mask].astype(np.float64) * scale_factor).astype(np.int32)
    return adjusted, prices


def _predict_raw_action(agent, obs):
    if isinstance(agent, RecurrentPPO):
        action, _ = agent.predict(obs, state=None, episode_start=np.ones((1,), dtype=bool), deterministic=True)
    else:
        action, _ = agent.predict(obs, deterministic=True)
    return np.array(action, dtype=np.float64)


def get_today_recommendations(state, runtime=None):
    runtime = runtime or get_runtime()
    arrays = runtime["arrays"]
    agents = runtime["agents"]
    date_to_idx = {_iso(d): i for i, d in enumerate(arrays.dates)}
    current_date = state["current_date"]
    if current_date not in date_to_idx:
        raise RuntimeConfigurationError(f"Current state date {current_date} is not available in the runtime dataset.")
    idx = date_to_idx[current_date]
    shares = _state_shares_vector(state, arrays)
    balance = float(state["model_balance"])
    monthly_peak = float(state.get("monthly_peak", state["model_portfolio_v"][-1]))
    agent = agents[state["active_agent"]]
    env = StockTradingEnv(arrays, i_start=idx, i_end=min(idx + 1, arrays.T), initial_capital=balance)
    obs, _ = env.reset()
    env.shares = shares.copy()
    env.balance = balance
    current_portfolio_value = _portfolio_value(balance, shares, arrays.prices[idx])
    env.portfolio_v = [current_portfolio_value]
    env.monthly_peak = monthly_peak
    raw_action = _predict_raw_action(agent, obs)
    adjusted, prices = _preview_actions(raw_action, arrays, idx, balance, shares, monthly_peak, current_portfolio_value)

    rows = []
    for i, ticker in enumerate(arrays.tickers):
        raw = float(raw_action[i])
        action = int(adjusted[i])
        if action > 0:
            signal = "BUY"
        elif action < 0:
            signal = "SELL"
        else:
            signal = "HOLD"
        abs_raw = abs(raw)
        if signal == "HOLD":
            conviction = "HOLD"
        elif abs_raw > 0.6:
            conviction = "HIGH"
        elif abs_raw > 0.3:
            conviction = "MEDIUM"
        else:
            conviction = "LOW"
        rows.append(
            {
                "ticker": ticker,
                "price": float(prices[i]),
                "signal": signal,
                "shares": action,
                "rawAction": raw,
                "conviction": conviction,
                "estimatedCost": float(abs(action) * prices[i]),
            }
        )
    rows.sort(key=recommendation_sort_key)
    return {
        "date": current_date,
        "agent": state["active_agent"],
        "regime": state["regime"],
        "recommendations": rows,
    }


def _status_payload(state):
    return {
        "currentDate": state["current_date"],
        "month": state["current_month"],
        "activeAgent": state["active_agent"],
        "regime": state["regime"],
        "vix": state["vix"],
        "sentiment": state["sentiment"],
        "yield10y": state["yield10y"],
        "initialCapital": state["initial_capital"],
        "portfolioValue": state["model_portfolio_v"][-1] if state["model_portfolio_v"] else state["initial_capital"],
    }


def get_status():
    return _status_payload(read_state())


def get_portfolio():
    state = read_state()
    return {
        "equityCurve": state["model_portfolio_v"],
        "metrics": compute_metrics(state["model_portfolio_v"]),
        "selLog": state["sel_log"],
        "tradeDates": state["trade_dates"],
    }


def simulate_user_portfolio(user_trades, arrays, initial_capital, relevant_dates=None):
    d2i = {str(pd.Timestamp(d).date()): i for i, d in enumerate(arrays.dates)}
    balance = float(initial_capital)
    shares = np.zeros(len(arrays.tickers))
    t2i = {ticker: i for i, ticker in enumerate(arrays.tickers)}
    pv = [initial_capital]
    dates = []
    trade_map = {}
    for trade in user_trades:
        trade_map.setdefault(trade["date"], []).append(trade)

    if relevant_dates:
        target_dates = [str(pd.Timestamp(d).date()) for d in relevant_dates if str(pd.Timestamp(d).date()) in d2i]
    else:
        target_dates = sorted(d2i.keys())

    last_prices = None
    for d in target_dates:
        idx = d2i[d]
        prices = arrays.prices[idx]
        last_prices = prices
        if d in trade_map:
            for trade in trade_map[d]:
                ti = t2i.get(trade["ticker"])
                delta = int(trade["sharesDelta"] if "sharesDelta" in trade else trade["shares_delta"])
                price = float(prices[ti])
                if delta > 0:
                    cost = delta * price * (1 + TRANSACTION_COST)
                    if cost <= balance:
                        balance -= cost
                        shares[ti] += delta
                elif delta < 0:
                    sell_n = min(-delta, int(shares[ti]))
                    balance += sell_n * price * (1 - TRANSACTION_COST)
                    shares[ti] -= sell_n
        val = balance + float((shares * prices).sum())
        pv.append(val)
        dates.append(d)
    holdings_value = float((shares * last_prices).sum()) if last_prices is not None else 0.0
    return {
        "portfolio_v": pv,
        "dates": dates,
        "metrics": compute_metrics(pv),
        "final_shares": {arrays.tickers[i]: int(shares[i]) for i in range(len(arrays.tickers))},
        "final_balance": balance,
        "final_holdings_value": holdings_value,
        "final_portfolio_value": pv[-1],
    }


def simulate_from_request(trades, initial_capital):
    runtime = get_runtime()
    state = read_state()
    return simulate_user_portfolio(trades, runtime["arrays"], initial_capital, relevant_dates=state.get("trade_dates"))


def bootstrap_state(force=False):
    if STATE_FILE.exists() and not force:
        return read_state()

    runtime = get_runtime(force=force)
    arrays = runtime["arrays"]
    agents = runtime["agents"]
    regime_series = runtime["regime_series"]
    gating_dataset = runtime["gating_dataset"]
    gating_net = runtime["gating_net"]
    val_i0 = runtime["val_i0"]
    val_i1 = runtime["val_i1"]

    trade_dates = [d for d in arrays.dates if pd.Timestamp(TRADE_START) <= pd.Timestamp(d) <= pd.Timestamp(date.today())]
    if not trade_dates:
        raise RuntimeConfigurationError("No trade dates are available for bootstrap.")

    months = split_months(arrays, trade_dates)
    balance = float(INITIAL_CAPITAL)
    shares = np.zeros(arrays.N, dtype=np.float64)
    monthly_peak = float(INITIAL_CAPITAL)
    portfolio_v = [float(INITIAL_CAPITAL)]
    trade_date_labels = []
    selection_log = []
    active_agent = AGENT_NAMES[0]
    active_regime = "unknown"

    for month_index, (m_i0, m_i1, label) in enumerate(months):
        if month_index == 0:
            sharpes = {name: validate_agent(agent, arrays, val_i0, val_i1) for name, agent in agents.items()}
        else:
            prev_i1 = months[month_index - 1][1]
            eval_i0 = max(0, prev_i1 - SHARPE_EVAL_DAYS)
            sharpes = {name: validate_agent(agent, arrays, eval_i0, prev_i1) for name, agent in agents.items()}

        month_date = arrays.dates[m_i0]
        regime = get_current_regime(regime_series, month_date)
        vix_now = float(arrays.vix[m_i0])
        sent_now = float(arrays.sentiment[m_i0])
        yld_now = float(arrays.yield10y[m_i0])
        winner = select_agent(regime, sharpes, gating_net, gating_dataset, vix_now, sent_now, yld_now)
        active_agent = winner
        active_regime = regime
        selection_log.append(
            {
                "month": label,
                "regime": regime,
                "selected": winner,
                "sharpes": {k: float(v) for k, v in sharpes.items()},
                "vix": vix_now,
                "sentiment": sent_now,
                "yield10y": yld_now,
            }
        )
        pv_window, balance, shares, monthly_peak = _run_agent(agents[winner], arrays, m_i0, m_i1, balance, shares, monthly_peak)
        portfolio_v.extend([float(v) for v in pv_window])
        trade_date_labels.extend([_iso(d) for d in arrays.dates[m_i0:m_i1]])

    current_date = trade_date_labels[-1]
    current_idx = {_iso(d): i for i, d in enumerate(arrays.dates)}[current_date]
    state = {
        "current_date": current_date,
        "current_month": _month_label(current_date),
        "active_agent": active_agent,
        "regime": active_regime,
        "vix": float(arrays.vix[current_idx]),
        "sentiment": float(arrays.sentiment[current_idx]),
        "yield10y": float(arrays.yield10y[current_idx]),
        "initial_capital": float(INITIAL_CAPITAL),
        "model_balance": float(balance),
        "model_shares": {arrays.tickers[i]: int(shares[i]) for i in range(arrays.N)},
        "model_portfolio_v": portfolio_v,
        "trade_dates": trade_date_labels,
        "sel_log": selection_log,
        "monthly_peak": float(monthly_peak),
        "last_recommendations": {},
    }
    state["last_recommendations"] = get_today_recommendations(state, runtime)
    return write_state(state)


def run_day():
    runtime = get_runtime(force=True)
    state = read_state()
    arrays = runtime["arrays"]
    agents = runtime["agents"]
    regime_series = runtime["regime_series"]
    gating_dataset = runtime["gating_dataset"]
    gating_net = runtime["gating_net"]
    date_to_idx = {_iso(d): i for i, d in enumerate(arrays.dates)}
    current_idx = date_to_idx[state["current_date"]]
    if current_idx >= arrays.T - 1:
        state["last_recommendations"] = get_today_recommendations(state, runtime)
        return write_state(state)

    next_idx = current_idx + 1
    next_date = arrays.dates[next_idx]
    active_agent = state["active_agent"]
    regime = get_current_regime(regime_series, next_date)
    if _month_label(next_date) != state["current_month"]:
        eval_i0 = max(0, next_idx - SHARPE_EVAL_DAYS)
        sharpes = {name: validate_agent(agent, arrays, eval_i0, next_idx) for name, agent in agents.items()}
        active_agent = select_agent(
            regime,
            sharpes,
            gating_net,
            gating_dataset,
            float(arrays.vix[next_idx]),
            float(arrays.sentiment[next_idx]),
            float(arrays.yield10y[next_idx]),
        )
        state["sel_log"].append(
            {
                "month": _month_label(next_date),
                "regime": regime,
                "selected": active_agent,
                "sharpes": {k: float(v) for k, v in sharpes.items()},
                "vix": float(arrays.vix[next_idx]),
                "sentiment": float(arrays.sentiment[next_idx]),
                "yield10y": float(arrays.yield10y[next_idx]),
            }
        )

    shares = _state_shares_vector(state, arrays)
    pv_window, balance, shares, monthly_peak = _run_agent(
        agents[active_agent],
        arrays,
        next_idx,
        next_idx + 1,
        float(state["model_balance"]),
        shares,
        float(state.get("monthly_peak", state["model_portfolio_v"][-1])),
    )

    state["current_date"] = _iso(next_date)
    state["current_month"] = _month_label(next_date)
    state["active_agent"] = active_agent
    state["regime"] = regime
    state["vix"] = float(arrays.vix[next_idx])
    state["sentiment"] = float(arrays.sentiment[next_idx])
    state["yield10y"] = float(arrays.yield10y[next_idx])
    state["model_balance"] = float(balance)
    state["model_shares"] = {arrays.tickers[i]: int(shares[i]) for i in range(arrays.N)}
    state["model_portfolio_v"].extend([float(v) for v in pv_window])
    state["trade_dates"].append(_iso(next_date))
    state["monthly_peak"] = float(monthly_peak)
    state["last_recommendations"] = get_today_recommendations(state, runtime)
    return write_state(state)
