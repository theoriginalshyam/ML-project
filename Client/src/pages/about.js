import TradingLayout from "../Mycomps/TradingLayout";

function About() {
  return (
    <TradingLayout
      title="About AlgoFlux"
      subtitle="AlgoFlux now operates as an ensemble trading decision-support workflow built around your trained RL agents, not the old single-stock LSTM forecast demo."
    >
      <section className="callout-card">
        <h3>What the platform does now</h3>
        <p>
          The model evaluates a 30-stock universe, selects an active agent based on market regime,
          and produces daily buy, sell, or hold recommendations that users can review before
          confirming their own portfolio decisions.
        </p>
      </section>
      <section className="card-grid two-up">
        <div className="metric-card">
          <h3>Model role</h3>
          <p className="metric-note">
            The ensemble acts as an advisor: it surfaces market context, chooses the active agent,
            and proposes position changes for each tracked stock.
          </p>
        </div>
        <div className="metric-card">
          <h3>User role</h3>
          <p className="metric-note">
            Users review those actions, adjust anything they disagree with, confirm the final set,
            and then track their own portfolio against the model's untouched run.
          </p>
        </div>
      </section>
    </TradingLayout>
  );
}

export default About;
