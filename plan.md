# AlgoFlux — Complete System Implementation Plan

## What the model actually outputs and how users fit in

The RL agent produces a **continuous action value between -1 and +1 for each of the 30 stocks**, every trading day. This gets multiplied by a volatility-adjusted limit (`vol_hmax`) to produce a concrete integer: how many shares to buy (positive) or sell (negative). Zero means hold.

The user role we're designing: **the model generates today's recommended trades for all 30 stocks — the user reviews them, adjusts any they disagree with, and confirms. The system then simulates the resulting portfolio and tracks it against the model's own unmodified run.** This turns the platform from a passive dashboard into an active decision-support tool where the model is an advisor, not an autopilot.

---

## System architecture overview

```
Client (React, port 3000)
  │  Login / Register (unchanged)
  │  Dashboard — market context, regime, VIX, sentiment
  │  Trade Review — today's recommendations, user edits, confirm
  │  Portfolio — user portfolio vs model portfolio equity curves
  │  History — monthly agent selection log
  │
Backend (Node/Express, port 5000)
  │  Auth unchanged
  │  /v1/ensemble/* — proxy to ML service
  │  /v1/portfolio/* — user portfolio CRUD in MongoDB
  │
ML Service (Flask, port 6969)
     /ensemble/recommendations — today's model actions per stock
     /ensemble/status          — regime, agent, VIX, sentiment
     /ensemble/portfolio       — model's own equity curve + metrics
     /ensemble/simulate        — given user's actual trades, compute their portfolio curve
     /ensemble/run-day         — advance the model one trading day (called by scheduler)
```

---

## Part 1 — ML Service (`ML_Models/inference_app.py`)

### 1a. What to extract from `ensemble_trading_v2.py`

Copy these directly into `inference_app.py` (do not import the training script):
- All constants: `TICKERS`, `AGENT_NAMES`, `REGIME_NAMES`, `INITIAL_CAPITAL`, `TRANSACTION_COST`, `HMAX`, `TARGET_STOCK_VOL`, `MIN_VOL_HMAX`, `MAX_VOL_HMAX`, `TURB_MIDPOINT`, `TURB_STEEPNESS`, `TURB_FLOOR`, `DD_THRESHOLD`, `N_REGIMES`, `N_AGENTS`, `GATING_INPUT_DIM`, `MIN_GATING_SAMPLES`, `BATCH_SIZE`, `BUFFER_SIZE`, `GRADIENT_STEPS`, `N_ENVS`, `LEARNING_STARTS`, `NET_ARCH`, `FINETUNE_LOOKBACK`, `SHARPE_EVAL_DAYS`, `REWARD_VOL_WINDOW`, `OVERTRADING_PENALTY`, `REGIME_WINDOW`, `FINETUNE_TIMESTEPS`
- All classes: `GatingNet`, `StockTradingEnv`, `MarketArrays`, `ProgressCallback`
- All functions: `download_data`, `download_macro`, `build_sentiment_series`, `compute_turbulence`, `compute_turbulence_forecast`, `fit_regime_hmm`, `label_regimes`, `get_current_regime`, `turb_scale`, `sharpe_ratio`, `sortino_ratio`, `compute_metrics`, `_clean`, `_gating_features`, `load_gating_dataset`, `save_gating_dataset`, `append_gating_sample`, `train_gating_net`, `save_gating_net`, `load_gating_net`, `select_agent`, `coldstart_select`, `_make_vec_env`, `load_agents`, `train_agents`, `validate_agent`, `split_months`, `_run_agent`, `get_finbert`, `vix_to_sentiment`, `build_sentiment_series`, `_norm_ts`
- Path variables: `BASE_DIR`, `AGENTS_DIR`, `GATING_DATA_FILE`, `GATING_MODEL_FILE`, `SENTIMENT_CACHE_FILE`

### 1b. State file schema (`ML_Models/output/state.json`)

```json
{
  "current_date": "2025-04-25",
  "current_month": "2025-04",
  "active_agent": "TQC",
  "regime": "bull_low_vol",
  "vix": 17.8,
  "sentiment": 0.38,
  "yield10y": 4.21,
  "initial_capital": 1000000,
  "model_balance": 187400.0,
  "model_shares": { "AAPL": 35, "MSFT": 22, ... },
  "model_portfolio_v": [1000000, 1008000, ...],
  "trade_dates": ["2025-01-02", "2025-01-03", ...],
  "sel_log": [
    {
      "month": "2025-01",
      "regime": "bull_low_vol",
      "selected": "TD3",
      "sharpes": { "TQC": 0.91, "CrossQ": 0.78, "TD3": 1.12, "RPPO": 0.65 },
      "vix": 14.2,
      "sentiment": 0.55,
      "yield10y": 4.05
    }
  ],
  "last_recommendations": {
    "date": "2025-04-25",
    "prices": { "AAPL": 213.4, "MSFT": 412.1, ... },
    "actions": { "AAPL": 3, "MSFT": -1, "JPM": 0, ... },
    "signals": { "AAPL": "BUY", "MSFT": "SELL", "JPM": "HOLD", ... },
    "raw_actions": { "AAPL": 0.72, "MSFT": -0.21, ... },
    "conviction": { "AAPL": "HIGH", "MSFT": "LOW", "JPM": "HOLD", ... }
  }
}
```

**Conviction** is derived from the absolute value of `raw_action`:
- `|raw| > 0.6` → HIGH
- `0.3 < |raw| <= 0.6` → MEDIUM
- `|raw| <= 0.3 and action != 0` → LOW
- `action == 0` → HOLD

### 1c. New function: `get_today_recommendations`

This is the core new function. It takes the current observation (today's market state) and runs `agent.predict(obs)` **without stepping the environment** — it only reads the action the model would take, then converts it to human-readable recommendations.

```python
def get_today_recommendations(agent, arrays, current_date_idx, model_shares, model_balance):
    """
    Run one prediction step without advancing environment state.
    Returns per-stock: raw_action, scaled_action (shares), signal, conviction, current_price.
    """
    env = StockTradingEnv(arrays, i_start=current_date_idx, i_end=current_date_idx + 1,
                          initial_capital=model_balance)
    obs, _ = env.reset()
    env.shares = model_shares.copy()

    if isinstance(agent, RecurrentPPO):
        action, _ = agent.predict(obs, deterministic=True)
    else:
        action, _ = agent.predict(obs, deterministic=True)

    # Scale exactly as the environment would
    turb_sc  = turb_scale(float(arrays.turb[current_date_idx]))
    drawdown = 0.0  # no prior step in single prediction
    scale    = turb_sc
    vh       = arrays.vol_hmax[current_date_idx]
    acts     = (action * scale * vh).astype(np.int32)
    prices   = arrays.prices[current_date_idx]

    result = {}
    for i, ticker in enumerate(arrays.tickers):
        raw   = float(action[i])
        act   = int(acts[i])
        price = float(prices[i])

        if act > 0:   signal = "BUY"
        elif act < 0: signal = "SELL"
        else:         signal = "HOLD"

        abs_raw = abs(raw)
        if signal == "HOLD":        conviction = "HOLD"
        elif abs_raw > 0.6:         conviction = "HIGH"
        elif abs_raw > 0.3:         conviction = "MEDIUM"
        else:                       conviction = "LOW"

        result[ticker] = {
            "raw_action":  raw,
            "shares":      act,
            "signal":      signal,
            "conviction":  conviction,
            "price":       price,
            "cost":        abs(act) * price,
        }
    return result
```

### 1d. New function: `simulate_user_portfolio`

Takes a list of the user's confirmed trade history (stored in MongoDB by the backend) and replays them against real prices to produce a portfolio value curve, then computes metrics.

```python
def simulate_user_portfolio(user_trades, arrays, initial_capital):
    """
    user_trades: list of { date, ticker, shares_delta }
                 shares_delta > 0 = buy, < 0 = sell
    Returns: { portfolio_v: [...], dates: [...], metrics: {...}, final_shares: {...} }
    """
    d2i     = {str(d.date()): i for i, d in enumerate(arrays.dates)}
    balance = float(initial_capital)
    shares  = np.zeros(len(arrays.tickers))
    t2i     = {t: i for i, t in enumerate(arrays.tickers)}
    pv      = [initial_capital]
    dates   = []

    # Group trades by date
    trade_map = {}
    for t in user_trades:
        trade_map.setdefault(t["date"], []).append(t)

    all_dates = sorted(d2i.keys())
    for d in all_dates:
        idx = d2i[d]
        prices = arrays.prices[idx]

        if d in trade_map:
            for trade in trade_map[d]:
                ti    = t2i.get(trade["ticker"])
                delta = int(trade["shares_delta"])
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

    return {
        "portfolio_v":   pv,
        "dates":         dates,
        "metrics":       compute_metrics(pv),
        "final_shares":  {arrays.tickers[i]: int(shares[i]) for i in range(len(arrays.tickers))},
        "final_balance": balance,
    }
```

### 1e. Flask endpoints

All endpoints check `Token` header against `SERVER_SECRET`.

**`POST /ensemble/status`**
Reads `state.json`. Returns: `activeAgent`, `regime`, `portfolioValue` (model's), `vix`, `sentiment`, `yield10y`, `month`, `initialCapital`.

**`POST /ensemble/recommendations`**
Reads `state.json`. Returns `last_recommendations` exactly as stored. If today's recommendations haven't been generated yet (date mismatch), calls `get_today_recommendations`, updates `state.json`, and returns fresh data. Response shape:
```json
{
  "date": "2025-04-25",
  "agent": "TQC",
  "regime": "bull_low_vol",
  "recommendations": {
    "AAPL": { "signal": "BUY", "shares": 3, "conviction": "HIGH", "price": 213.4, "cost": 640.2, "raw_action": 0.72 },
    "MSFT": { "signal": "SELL", "shares": -1, "conviction": "LOW", "price": 412.1, "cost": 412.1, "raw_action": -0.18 },
    "JPM":  { "signal": "HOLD", "shares": 0, "conviction": "HOLD", "price": 198.3, "cost": 0, "raw_action": 0.04 }
  }
}
```

**`POST /ensemble/portfolio`**
Returns: model equity curve, metrics, `selLog`, `tradeDates`. All from `state.json`.

**`POST /ensemble/simulate`**
Body: `{ "trades": [...], "initialCapital": 1000000 }`. Calls `simulate_user_portfolio`. Returns user portfolio curve + metrics. This is called by the backend when the user wants to see their portfolio vs. the model.

**`POST /ensemble/run-day`**
Heavy endpoint. Called by the backend scheduler at market close each trading day. Steps the model forward one day: fetches latest prices, runs the agent, updates `model_shares`, `model_balance`, `model_portfolio_v`, `trade_dates`, and regenerates `last_recommendations` for tomorrow. If it is the first day of a new month, also runs regime detection, agent selection, gating network update, and fine-tuning.

### 1f. Scheduler

Add a separate `scheduler.py` in `ML_Models/` that uses `APScheduler`:
```python
from apscheduler.schedulers.blocking import BlockingScheduler
import requests, os

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=16, minute=30, timezone='America/New_York')
def run_daily():
    requests.post('http://localhost:6969/ensemble/run-day',
                  headers={'Token': os.getenv('SERVER_SECRET')})

scheduler.start()
```

Run this as a separate process alongside `inference_app.py`. Add `APScheduler` to `requirements.txt`.

---

## Part 2 — MongoDB: new `UserPortfolio` model

Create `Backend/src/models/portfolio.model.js`:

```javascript
const mongoose = require('mongoose');

const tradeSchema = mongoose.Schema({
  date:         { type: String, required: true },   // "YYYY-MM-DD"
  ticker:       { type: String, required: true },
  sharesDelta:  { type: Number, required: true },   // + buy, - sell
  priceAtTime:  { type: Number, required: true },
  modelSignal:  { type: String },                   // BUY / SELL / HOLD (what model recommended)
  modelShares:  { type: Number },                   // what model recommended in shares
  userOverride: { type: Boolean, default: false },  // did user change the recommendation?
});

const portfolioSchema = mongoose.Schema({
  user:           { type: mongoose.SchemaTypes.ObjectId, ref: 'User', required: true, unique: true },
  initialCapital: { type: Number, required: true, default: 1000000 },
  confirmedDays:  { type: [String], default: [] },  // dates user has reviewed
  trades:         { type: [tradeSchema], default: [] },
}, { timestamps: true });

module.exports = mongoose.model('UserPortfolio', portfolioSchema);
```

---

## Part 3 — Backend: new routes and controllers

### 3a. `ensemble.controller.js` — proxy calls to ML service

```javascript
const proxy = (path, bodyFn = () => ({})) => catchAsync(async (req, res) => {
  request.post({
    url: `http://localhost:6969${path}`,
    json: true,
    body: bodyFn(req),
    headers: { Token: process.env.SERVER_SECRET }
  }, (err, mlRes, body) => {
    if (err) return res.status(502).json({ message: 'ML service unavailable' });
    res.status(mlRes.statusCode).json(body);
  });
});

module.exports = {
  getStatus:         proxy('/ensemble/status'),
  getRecommendations:proxy('/ensemble/recommendations'),
  getModelPortfolio: proxy('/ensemble/portfolio'),
};
```

### 3b. `portfolio.controller.js` — user portfolio logic

**`GET /portfolio/me`** — Fetch user's portfolio document from MongoDB. If none exists, create one with `initialCapital: 1000000`.

**`GET /portfolio/recommendations`** — Get today's recommendations from ML service AND cross-reference with user's existing holdings from MongoDB. Enrich each recommendation with: `currentlyHeld` (shares user already holds), `estimatedCost` (shares × price), `wouldExceedBudget` (bool based on user's simulated balance).

**`POST /portfolio/confirm`** — Body: `{ date, trades: [{ ticker, sharesDelta }] }`. Validates the date hasn't already been confirmed. Fetches today's price for each ticker from `state.json`. Saves each trade to MongoDB with `priceAtTime`, `modelSignal`, `modelShares`, and sets `userOverride: true` if `sharesDelta !== modelShares`. Appends date to `confirmedDays`.

**`POST /portfolio/skip`** — Body: `{ date }`. Confirms the day with zero trades (user chose not to act today). Appends date to `confirmedDays` with no trade records.

**`GET /portfolio/simulate`** — Reads all user trades from MongoDB, calls `/ensemble/simulate` on ML service, returns user portfolio curve + metrics. Also returns model portfolio curve from state for comparison.

**`GET /portfolio/history`** — Returns the full trade log for the user, grouped by month, with a summary of how many recommendations they followed vs. overrode.

### 3c. Routes

**`ensemble.route.js`**:
```
POST /v1/ensemble/status             → auth() → getStatus
POST /v1/ensemble/recommendations    → auth() → getRecommendations
POST /v1/ensemble/portfolio          → auth() → getModelPortfolio
```

**`portfolio.route.js`**:
```
GET  /v1/portfolio/me                → auth() → getMyPortfolio
GET  /v1/portfolio/recommendations   → auth() → getEnrichedRecommendations
POST /v1/portfolio/confirm           → auth() → confirmDay
POST /v1/portfolio/skip              → auth() → skipDay
GET  /v1/portfolio/simulate          → auth() → simulateUserPortfolio
GET  /v1/portfolio/history           → auth() → getTradeHistory
```

Register both in `routes/v1/index.js`.

---

## Part 4 — Frontend (`Client/src/`)

### 4a. API layer (`src/api/`)

Create `ensemble.js` and `portfolio.js` mirroring each backend route above. All calls use `Authorization: Bearer <token>` header. Token is read from wherever the existing app stores it.

### 4b. Pages and components

**`/dashboard` — Dashboard page**

Components:
- `StatusBar` — regime badge (colour-coded), active agent pill, VIX gauge (0–40 scale), sentiment bar (-1 to +1), 10-year yield. Polling every 60 seconds.
- `MarketContext` — a short text block auto-generated from the status: e.g. "The model is currently in a **bull_low_vol** regime and has selected **TQC** as this month's agent. VIX at 17.8 suggests moderate calm."
- `PortfolioSummary` — two side-by-side cards: "Model Portfolio" (value, return %, Sharpe) and "Your Portfolio" (same metrics from simulate endpoint). If user has no confirmed days yet, "Your Portfolio" shows a prompt: "Review today's recommendations to start tracking your portfolio."
- `TodayBanner` — a prominent banner: "Today's recommendations are ready. [Review & Confirm →]" or "You've confirmed today's trades. ✓" depending on whether today is in `confirmedDays`.

**`/recommendations` — Trade Review page** (the most important page)

This is where the user role lives. Layout:

Top section: market context strip (agent, regime, VIX, sentiment, date).

Main table — one row per stock, columns:
| Ticker | Price | Signal | Conviction | Model Suggests | Your Decision | Est. Cost |
|--------|-------|--------|------------|----------------|---------------|-----------|

- **Signal** — colour-coded pill: BUY (green), SELL (red), HOLD (grey)
- **Conviction** — HIGH / MEDIUM / LOW / HOLD
- **Model Suggests** — e.g. "Buy 3 shares" or "Sell 1 share" or "Hold"
- **Your Decision** — a number input pre-filled with the model's suggestion. User can change it. Changing it highlights the row in amber to indicate an override. Range: can be negative (sell) up to `currentlyHeld` shares, or positive (buy) constrained by simulated remaining balance.
- **Est. Cost** — updates live as user changes the number

Below the model's suggestion number input, show: `Currently holding: 35 shares`.

Stocks are sorted: BUY HIGH at top, then BUY MEDIUM, BUY LOW, then HOLDs, then SELL LOW, SELL MEDIUM, SELL HIGH at bottom.

Filter bar: buttons to show All / BUY only / SELL only / Overridden.

Bottom bar (sticky):
- "Estimated cash used: $X,XXX of $XXX,XXX available"
- "Overriding X of Y recommendations"
- [Skip Today] button — confirms with zero trades
- [Confirm Trades] button — posts to `/portfolio/confirm`

After confirming, redirect to `/portfolio`.

**`/portfolio` — Portfolio page**

Top: metrics row for user portfolio — Cum. Return, Ann. Return, Sharpe, Sortino, Max Drawdown.

Chart: `recharts` LineChart with two lines — "Your Portfolio" (primary colour) and "Model Portfolio" (dashed). X-axis: dates of confirmed days. Y-axis: portfolio value in dollars. If user has fewer than 2 confirmed days, show placeholder.

Below chart: "You vs. Model" summary — a simple callout: "You have outperformed / underperformed the model by X% over Y trading days. You followed Z% of recommendations."

Trade history table: grouped by month. Columns: Date | Ticker | Action | Shares | Price | You vs. Model (green tick if user matched model, amber flag if override).

**`/history` — Monthly Selection Log page**

Table: Month | Regime | Selected Agent | Agent Sharpes (TQC / CrossQ / TD3 / RPPO) | VIX | Sentiment. Each regime cell colour-coded. Each agent's Sharpe cell highlights the winner.

**Navigation**

Sidebar or top nav links: Dashboard · Recommendations · My Portfolio · History. Add a badge on the Recommendations link showing "1 pending" when today hasn't been confirmed yet.

---

## Part 5 — User flow end to end

This is the complete experience from a user's perspective once the system is running:

1. User logs in and lands on Dashboard. They see the current regime, active agent, and a banner saying today's recommendations are ready.
2. They click "Review & Confirm" and go to the Recommendations page. They see all 30 stocks with the model's suggested trades pre-filled.
3. They review. They agree with most but change MSFT from "Sell 1" to "Hold 0" and change BA from "Buy 2" to "Buy 5". These rows turn amber.
4. They see the estimated cost update in the sticky bar. They click "Confirm Trades".
5. The backend saves their actual trades to MongoDB with override flags on MSFT and BA.
6. They are redirected to My Portfolio, where they can see their equity curve (which starts today) and a note that they need more days of data for meaningful metrics.
7. The next trading day, they get a new banner. They can review again. Over time their curve diverges from the model's, for better or worse.
8. On the History page they can see the month-by-month log of which agent ran and why.

---

## Part 6 — `requirements.txt` additions for ML service

```
stable-baselines3[extra]
sb3-contrib
yfinance
gymnasium
hmmlearn
scikit-learn
transformers
accelerate
sentencepiece
torch
flask
python-dotenv
pandas
numpy
apscheduler
```

---

## Deployment notes for the agent

- `inference_app.py` and `scheduler.py` are two separate processes, both run from `ML_Models/` with the venv activated.
- `state.json` must exist before either process starts. Provide an initialised version.
- The `/ensemble/run-day` endpoint is the only one that writes to `state.json`. All other endpoints are read-only with respect to state.
- MongoDB needs the new `UserPortfolio` collection — the model creates it automatically on first `POST /portfolio/confirm`.
- The existing auth, user management, and token routes are untouched.
- The old `/v1/ml` routes can remain but should be removed from the frontend navigation.