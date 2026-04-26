import { useEffect, useMemo, useState } from "react";
import TradingLayout from "../Mycomps/TradingLayout";
import SimpleLineChart from "../Mycomps/SimpleLineChart";
import { getPortfolioHistory, getPortfolioSimulation } from "../api/portfolio";

export default function PortfolioPage() {
  const [simulation, setSimulation] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [simulationPayload, historyPayload] = await Promise.all([
          getPortfolioSimulation(),
          getPortfolioHistory(),
        ]);
        if (!mounted) return;
        setSimulation(simulationPayload);
        setHistory(historyPayload);
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.message || "Unable to load portfolio details.");
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

  const chartLabels = useMemo(() => {
    if (!simulation) return [];
    const userDates = simulation.user?.dates || [];
    const modelDates = simulation.model?.tradeDates || [];
    const maxLength = Math.max(
      simulation.user?.portfolio_v?.length || 0,
      simulation.model?.equityCurve?.length || 0
    );
    return Array.from({ length: maxLength }).map((_, index) => {
      if (index === 0) {
        return "Start";
      }
      return modelDates[index - 1] || userDates[index - 1] || `Day ${index}`;
    });
  }, [simulation]);

  return (
    <TradingLayout
      title="My Portfolio"
      subtitle="See how your confirmed decisions compare against the model's own unmodified run."
    >
      {loading ? <div className="empty-state">Loading portfolio comparison...</div> : null}
      {!loading && error ? <div className="error-banner">{error}</div> : null}
      {!loading && simulation ? (
        <>
          <section className="card-grid two-up">
            <div className="metric-card">
              <h3>Your Portfolio</h3>
              <p className="metric-value">
                {simulation.user?.portfolio_v?.length
                  ? `$${simulation.user.portfolio_v[simulation.user.portfolio_v.length - 1].toFixed(2)}`
                  : "$0.00"}
              </p>
              <p className="metric-note">
                Cash: ${Number(simulation.user?.final_balance || 0).toFixed(2)} | Holdings: $
                {Number(simulation.user?.final_holdings_value || 0).toFixed(2)}
              </p>
              <ul className="metric-list">
                {Object.entries(simulation.user?.metrics || {}).map(([key, value]) => (
                  <li key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ul>
            </div>
            <div className="metric-card">
              <h3>Model Portfolio</h3>
              <p className="metric-value">
                {simulation.model?.equityCurve?.length
                  ? `$${simulation.model.equityCurve[simulation.model.equityCurve.length - 1].toFixed(2)}`
                  : "$0.00"}
              </p>
              <ul className="metric-list">
                {Object.entries(simulation.model?.metrics || {}).map(([key, value]) => (
                  <li key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <SimpleLineChart
            userSeries={simulation.user?.portfolio_v || []}
            modelSeries={simulation.model?.equityCurve || []}
            labels={chartLabels}
          />

          <section className="callout-card">
            <h3>You vs. Model</h3>
            <p>
              You have followed {simulation.summary?.followRate || 0}% of the stored recommendations
              across {simulation.summary?.totalTrades || 0} recorded trades.
            </p>
            <p className="metric-note">
              Confirming a recommendation records the trade immediately in the simulated portfolio on that
              recommendation date. It does not send a real broker order.
            </p>
          </section>

          <section className="table-card">
            <h3>Trade History</h3>
            {!history?.months?.length ? (
              <div className="empty-state">No confirmed trades yet.</div>
            ) : (
              history.months.map((month) => (
                <div key={month.month} className="history-month">
                  <h4>{month.month}</h4>
                  <table className="recommendation-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Ticker</th>
                        <th>Action</th>
                        <th>Shares</th>
                        <th>Price</th>
                        <th>You vs. Model</th>
                      </tr>
                    </thead>
                    <tbody>
                      {month.trades.map((trade) => (
                        <tr key={`${trade.date}-${trade.ticker}`}>
                          <td>{trade.date}</td>
                          <td>{trade.ticker}</td>
                          <td>{trade.sharesDelta > 0 ? "BUY" : trade.sharesDelta < 0 ? "SELL" : "HOLD"}</td>
                          <td>{trade.sharesDelta}</td>
                          <td>${Number(trade.priceAtTime || 0).toFixed(2)}</td>
                          <td>{trade.userOverride ? "Override" : "Matched model"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))
            )}
          </section>
        </>
      ) : null}
    </TradingLayout>
  );
}
