import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import TradingLayout from "../Mycomps/TradingLayout";
import {
  confirmPortfolioDay,
  getPortfolioRecommendations,
  skipPortfolioDay,
} from "../api/portfolio";

const signalFilter = (row, filter) => {
  if (filter === "buy") return row.signal === "BUY";
  if (filter === "sell") return row.signal === "SELL";
  if (filter === "overridden") return row.decision !== row.shares;
  return true;
};

export default function RecommendationsPage() {
  const navigate = useNavigate();
  const [payload, setPayload] = useState(null);
  const [decisions, setDecisions] = useState({});
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getPortfolioRecommendations();
        if (!mounted) return;
        setPayload(data);
        setDecisions(
          Object.fromEntries(data.recommendations.map((item) => [item.ticker, item.shares]))
        );
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.message || "Unable to load recommendations.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const rows = useMemo(() => {
    if (!payload) return [];
    return payload.recommendations.map((row) => ({
      ...row,
      decision: Number(decisions[row.ticker] ?? row.shares),
      override: Number(decisions[row.ticker] ?? row.shares) !== row.shares,
    }));
  }, [payload, decisions]);

  const displayedRows = rows.filter((row) => signalFilter(row, filter));
  const sellProceeds = rows
    .filter((row) => row.decision < 0)
    .reduce((sum, row) => sum + Math.abs(row.decision) * row.price * 0.999, 0);
  const cashUsed = rows
    .filter((row) => row.decision > 0)
    .reduce((sum, row) => sum + row.decision * row.price * 1.001, 0);
  const availableCash = (payload?.remainingCash || 0) + sellProceeds;
  const overrides = rows.filter((row) => row.override).length;
  const alreadyConfirmed = payload?.confirmedDays?.includes(payload?.date);

  const updateDecision = (ticker, value) => {
    setDecisions((current) => ({ ...current, [ticker]: Number(value) }));
  };

  const submitTrades = async () => {
    if (!payload) return;
    setSubmitting(true);
    setError("");
    try {
      await confirmPortfolioDay({
        date: payload.date,
        trades: rows.map((row) => ({
          ticker: row.ticker,
          sharesDelta: row.decision,
        })),
      });
      navigate("/portfolio");
    } catch (err) {
      setError(err.response?.data?.message || "Unable to confirm trades.");
    } finally {
      setSubmitting(false);
    }
  };

  const skipDay = async () => {
    if (!payload) return;
    setSubmitting(true);
    setError("");
    try {
      await skipPortfolioDay({ date: payload.date });
      navigate("/portfolio");
    } catch (err) {
      setError(err.response?.data?.message || "Unable to skip today.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <TradingLayout
      title="Recommendations"
      subtitle="Review the model's daily trade suggestions, adjust anything you disagree with, and confirm the portfolio you actually want to run."
    >
      {loading ? <div className="empty-state">Loading today's recommendation set...</div> : null}
      {!loading && error ? <div className="error-banner">{error}</div> : null}
      {!loading && payload ? (
        <>
          <section className="context-strip">
            <span>{payload.date}</span>
            <span>Agent: {payload.agent}</span>
            <span>Regime: {payload.regime}</span>
            <span>Available cash: ${availableCash.toFixed(2)}</span>
          </section>

          {alreadyConfirmed ? <div className="empty-state">You already confirmed this trading day. Head to My Portfolio to review the result.</div> : null}

          <div className="filter-row">
            {[
              ["all", "All"],
              ["buy", "BUY only"],
              ["sell", "SELL only"],
              ["overridden", "Overridden"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={`filter-chip ${filter === value ? "active" : ""}`}
                onClick={() => setFilter(value)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>

          <section className="table-card">
            <table className="recommendation-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Price</th>
                  <th>Signal</th>
                  <th>Conviction</th>
                  <th>Model Suggests</th>
                  <th>Your Decision</th>
                  <th>Est. Cost</th>
                  <th>Held</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map((row) => (
                  <tr key={row.ticker} className={row.override ? "row-override" : ""}>
                    <td>{row.ticker}</td>
                    <td>${row.price.toFixed(2)}</td>
                    <td>
                      <span className={`signal-pill ${row.signal.toLowerCase()}`}>{row.signal}</span>
                    </td>
                    <td>{row.conviction}</td>
                    <td>{row.shares > 0 ? `Buy ${row.shares}` : row.shares < 0 ? `Sell ${Math.abs(row.shares)}` : "Hold"}</td>
                    <td>
                      <input
                        className="decision-input"
                        type="number"
                        value={row.decision}
                        onChange={(event) => updateDecision(row.ticker, event.target.value)}
                      />
                    </td>
                    <td>${(Math.abs(row.decision) * row.price).toFixed(2)}</td>
                    <td>{row.currentlyHeld}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {!alreadyConfirmed ? (
            <section className="sticky-summary">
              <div>
                Estimated cash used: <strong>${cashUsed.toFixed(2)}</strong> of ${availableCash.toFixed(2)} available
              </div>
              <div>
                Overriding <strong>{overrides}</strong> of {rows.length} recommendations
              </div>
              <div className="summary-actions">
                <button type="button" className="secondary-button" onClick={skipDay} disabled={submitting}>
                  Skip Today
                </button>
                <button
                  type="button"
                  className="primary-button"
                  onClick={submitTrades}
                  disabled={submitting || cashUsed > availableCash}
                >
                  Confirm Trades
                </button>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </TradingLayout>
  );
}
