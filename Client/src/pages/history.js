import { useEffect, useState } from "react";
import TradingLayout from "../Mycomps/TradingLayout";
import { getEnsemblePortfolio } from "../api/ensemble";
import { getPortfolioHistory } from "../api/portfolio";

export default function HistoryPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [portfolioPayload, historyPayload] = await Promise.all([
          getEnsemblePortfolio(),
          getPortfolioHistory(),
        ]);
        if (!mounted) return;
        setPortfolio(portfolioPayload);
        setHistory(historyPayload);
      } catch (err) {
        if (mounted) {
          setError(err.response?.data?.message || "Unable to load history.");
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

  return (
    <TradingLayout
      title="History"
      subtitle="Track how the ensemble selected agents over time, and how closely your choices matched the model."
    >
      {loading ? <div className="empty-state">Loading monthly selection history...</div> : null}
      {!loading && error ? <div className="error-banner">{error}</div> : null}
      {!loading && portfolio ? (
        <>
          <section className="callout-card">
            <h3>User Summary</h3>
            <p>
              Followed {history?.summary?.followed || 0} recommendations and overrode{" "}
              {history?.summary?.overridden || 0}.
            </p>
          </section>

          <section className="table-card">
            <table className="recommendation-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Regime</th>
                  <th>Selected Agent</th>
                  <th>TQC</th>
                  <th>CrossQ</th>
                  <th>TD3</th>
                  <th>RPPO</th>
                  <th>VIX</th>
                  <th>Sentiment</th>
                </tr>
              </thead>
              <tbody>
                {(portfolio.selLog || []).map((entry) => (
                  <tr key={`${entry.month}-${entry.selected}`}>
                    <td>{entry.month}</td>
                    <td>{entry.regime}</td>
                    <td>{entry.selected}</td>
                    <td>{Number(entry.sharpes?.TQC || 0).toFixed(2)}</td>
                    <td>{Number(entry.sharpes?.CrossQ || 0).toFixed(2)}</td>
                    <td>{Number(entry.sharpes?.TD3 || 0).toFixed(2)}</td>
                    <td>{Number(entry.sharpes?.RPPO || 0).toFixed(2)}</td>
                    <td>{Number(entry.vix || 0).toFixed(2)}</td>
                    <td>{Number(entry.sentiment || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}
    </TradingLayout>
  );
}
