import Navbar from "./Navbar";
import Footerc from "./Footer";
import "../stylesheets/trading.css";

export default function TradingLayout({ title, subtitle, children }) {
  return (
    <div className="trading-page">
      <Navbar />
      <main className="trading-main">
        <section className="page-hero">
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </section>
        {children}
      </main>
      <Footerc />
    </div>
  );
}
