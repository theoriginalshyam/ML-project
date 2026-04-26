import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import TradingLayout from "../Mycomps/TradingLayout";
import { getEnsembleStatus } from "../api/ensemble";
import { getPortfolioSimulation } from "../api/portfolio";

export default function Home() {
  const [status, setStatus] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [statusPayload, simulationPayload] = await Promise.all([
          getEnsembleStatus(),
          getPortfolioSimulation(),
        ]);
        if (!mounted) return;
        setStatus(statusPayload);
        setSimulation(simulationPayload);
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.message || "Unable to load dashboard context.");
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

  const pending =
    status && simulation ? !simulation.confirmedDays?.includes(status.currentDate) : false;

  return (
    <TradingLayout
      title="Dashboard"
      subtitle="See the model's current market stance, today's recommendation state, and how your portfolio is diverging from the ensemble."
    >
      {loading ? <div className="empty-state">Loading live market context...</div> : null}
      {!loading && error ? <div className="error-banner">{error}</div> : null}
      {!loading && status ? (
        <>
          <section className={`banner-card ${pending ? "pending" : "done"}`}>
            <div>
              <strong>{pending ? "Today's recommendations are ready." : "Today's trading day is already confirmed."}</strong>
              <p>
                {pending
                  ? "Review the model's trades and confirm your own portfolio decisions."
                  : "You can head to My Portfolio to review how that decision is tracking."}
              </p>
            </div>
            <Link className="primary-button link-button" to={pending ? "/recommendations" : "/portfolio"}>
              {pending ? "Review & Confirm" : "Open Portfolio"}
            </Link>
          </section>

          <section className="card-grid">
            <div className="metric-card">
              <h3>Active Agent</h3>
              <p className="metric-value">{status.activeAgent}</p>
              <p className="metric-note">{status.regime}</p>
            </div>
            <div className="metric-card">
              <h3>VIX</h3>
              <p className="metric-value">{Number(status.vix).toFixed(2)}</p>
              <p className="metric-note">Current fear gauge</p>
            </div>
            <div className="metric-card">
              <h3>Sentiment</h3>
              <p className="metric-value">{Number(status.sentiment).toFixed(2)}</p>
              <p className="metric-note">News + VIX proxy signal</p>
            </div>
            <div className="metric-card">
              <h3>10Y Yield</h3>
              <p className="metric-value">{Number(status.yield10y).toFixed(2)}</p>
              <p className="metric-note">Macro context</p>
            </div>
          </section>

          <section className="card-grid two-up">
            <div className="metric-card">
              <h3>Model Portfolio</h3>
              <p className="metric-value">${Number(status.portfolioValue).toFixed(2)}</p>
              <ul className="metric-list">
                {Object.entries(simulation?.model?.metrics || {}).map(([key, value]) => (
                  <li key={key}>
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </li>
                ))}
              </ul>
            </div>
            <div className="metric-card">
              <h3>Your Portfolio</h3>
              <p className="metric-value">
                {simulation?.user?.portfolio_v?.length
                  ? `$${simulation.user.portfolio_v[simulation.user.portfolio_v.length - 1].toFixed(2)}`
                  : "$0.00"}
              </p>
              {simulation?.summary?.totalTrades ? (
                <ul className="metric-list">
                  {Object.entries(simulation?.user?.metrics || {}).map(([key, value]) => (
                    <li key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="metric-note">Review today's recommendations to start tracking your own portfolio.</p>
              )}
            </div>
          </section>
        </>
      ) : null}
    </TradingLayout>
  );
}
