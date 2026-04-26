import TradingLayout from "../Mycomps/TradingLayout";
import "../stylesheets/learn.css";

const learningTracks = [
  {
    title: "Market Basics",
    summary: "Build a clean mental model of how exchanges, listings, indices, and order flow work.",
    audience: "Best for first-time investors",
    format: "Read",
    link: "https://www.investopedia.com/terms/s/stockmarket.asp",
  },
  {
    title: "Starting in Stocks",
    summary: "Learn position sizing, account setup, and what to think through before your first trade.",
    audience: "Best for new participants",
    format: "Read",
    link: "https://www.investopedia.com/articles/basics/06/invest1000.asp",
  },
  {
    title: "Structured Market Primer",
    summary: "A more guided introduction to market structure, participants, and basic terminology.",
    audience: "Best for step-by-step learners",
    format: "Course",
    link: "https://zerodha.com/varsity/module/introduction-to-stock-markets/",
  },
  {
    title: "Stock Analysis",
    summary: "Understand the difference between evaluating a company and reacting to a price chart.",
    audience: "Best for research-focused users",
    format: "Read",
    link: "https://www.investopedia.com/terms/s/stock-analysis.asp#:~:text=Stock%20analysis%20involves%20comparing%20a,growing%2C%20stable%2C%20or%20deteriorating.",
  },
  {
    title: "Investing Strategies",
    summary: "Compare long-term investing styles and get a feel for where your own temperament fits.",
    audience: "Best for strategy framing",
    format: "Read",
    link: "https://www.fool.com/how-to-invest",
  },
];

const financeResources = [
  {
    title: "Finance Basics",
    detail: "Personal finance foundations, budgeting, and money habits that support better investing.",
    link: "https://www.khanacademy.org/college-careers-more/personal-finance",
  },
  {
    title: "Financial Resources",
    detail: "A broader look at how financial resources are managed in real systems and organizations.",
    link: "https://online.york.ac.uk/financial-resources-what-are-they-and-how-are-they-managed/",
  },
  {
    title: "Financial Planning",
    detail: "How to think about goals, risk, timelines, and portfolio decisions as one connected plan.",
    link: "https://smartasset.com/financial-advisor/financial-planning-explained",
  },
  {
    title: "Understanding Stocks",
    detail: "A concise primer on what owning stock actually means and how shares behave in the market.",
    link: "https://dfi.wa.gov/financial-education/information/basics-investing-stocks#:~:text=Stocks%20are%20a%20type%20of,shares%20on%20the%20stock%20market.",
  },
];

const books = [
  {
    title: "The Intelligent Investor",
    author: "Benjamin Graham",
    detail: "A classic on discipline, valuation, and surviving market noise with a long-term mindset.",
  },
  {
    title: "A Random Walk Down Wall Street",
    author: "Burton G. Malkiel",
    detail: "A practical overview of markets, efficiency, and how different investment styles stack up.",
  },
  {
    title: "Stocks for the Long Run",
    author: "Jeremy J. Siegel",
    detail: "Historical context on equities as an asset class and why time horizon changes everything.",
  },
  {
    title: "Common Stocks and Uncommon Profits",
    author: "Philip Fisher",
    detail: "A thoughtful framework for judging business quality beyond short-term market motion.",
  },
  {
    title: "How to Make Money in Stocks",
    author: "William J. O'Neil",
    detail: "More trading-oriented, with emphasis on momentum, screening, and chart-based timing.",
  },
  {
    title: "The Essays of Warren Buffett",
    author: "Warren Buffett and Lawrence A. Cunningham",
    detail: "A clean window into capital allocation, company quality, and patient decision-making.",
  },
];

const videoPrimers = [
  {
    title: "Stock Market Basics",
    detail: "A quick visual warm-up if you prefer to start with an overview instead of reading.",
    link: "https://www.youtube.com/watch?v=Xn7KWR9EOGQ",
  },
  {
    title: "How to Start Investing",
    detail: "Useful for understanding the first practical decisions before placing capital.",
    link: "https://www.youtube.com/watch?v=3UF0ymVdYLA",
  },
  {
    title: "Advanced Stock Analysis",
    detail: "A stronger fit once you already understand the basics and want deeper research methods.",
    link: "https://www.youtube.com/watch?v=eynxyoKgpng",
  },
];

const marketSites = [
  {
    title: "Yahoo Finance",
    detail: "Fast quote lookup, company pages, calendars, and lightweight headline monitoring.",
    link: "https://finance.yahoo.com/",
  },
  {
    title: "Bloomberg Markets",
    detail: "Macro-heavy coverage with a good feel for rates, policy, and institutional context.",
    link: "https://www.bloomberg.com/markets",
  },
  {
    title: "CNBC Business",
    detail: "Broad market coverage with frequent updates and a more trading-desk style rhythm.",
    link: "https://www.cnbc.com/business/",
  },
  {
    title: "Nasdaq",
    detail: "Useful for listings, market data, and a more exchange-centered reference point.",
    link: "https://www.nasdaq.com/",
  },
  {
    title: "Investing.com",
    detail: "Dense market monitoring across equities, rates, commodities, and economic releases.",
    link: "https://www.investing.com/",
  },
];

function ExternalResourceCard({ title, detail, link, format, audience }) {
  return (
    <article className="learn-resource-card">
      <div className="learn-resource-header">
        <h3>{title}</h3>
        {format ? <span className="learn-chip">{format}</span> : null}
      </div>
      <p>{detail}</p>
      {audience ? <p className="learn-resource-meta">{audience}</p> : null}
      <a href={link} className="learn-action" target="_blank" rel="noopener noreferrer">
        Open Resource
      </a>
    </article>
  );
}

function Learn() {
  return (
    <TradingLayout
      title="Learn"
      subtitle="A curated study surface for users who want stronger intuition before following, editing, or rejecting model trade suggestions."
    >
      <section className="learn-overview">
        <div className="learn-overview-card learn-overview-accent">
          <p className="learn-kicker">Study Flow</p>
          <h2>Go from market basics to portfolio judgment in one place.</h2>
          <p className="learn-copy">
            The goal here is not to drown you in links. It is to give you a cleaner path:
            understand the market, learn how to evaluate ideas, and build enough confidence to
            make deliberate decisions when the model speaks.
          </p>
        </div>
        <div className="learn-overview-grid">
          <article className="learn-stat-card">
            <span className="learn-stat-value">5</span>
            <span className="learn-stat-label">Core learning tracks</span>
          </article>
          <article className="learn-stat-card">
            <span className="learn-stat-value">6</span>
            <span className="learn-stat-label">Foundational books</span>
          </article>
          <article className="learn-stat-card">
            <span className="learn-stat-value">5</span>
            <span className="learn-stat-label">Reference market sites</span>
          </article>
        </div>
      </section>

      <section className="learn-section">
        <div className="learn-section-heading">
          <h2>Learning Tracks</h2>
          <p>Start here if you want a more intentional sequence instead of browsing at random.</p>
        </div>
        <div className="learn-resource-grid learn-resource-grid-large">
          {learningTracks.map((track) => (
            <ExternalResourceCard
              key={track.title}
              title={track.title}
              detail={track.summary}
              link={track.link}
              format={track.format}
              audience={track.audience}
            />
          ))}
        </div>
      </section>

      <section className="learn-section">
        <div className="learn-section-heading">
          <h2>Finance Context</h2>
          <p>Use these when you want stronger grounding around planning, ownership, and risk.</p>
        </div>
        <div className="learn-resource-grid">
          {financeResources.map((resource) => (
            <ExternalResourceCard
              key={resource.title}
              title={resource.title}
              detail={resource.detail}
              link={resource.link}
            />
          ))}
        </div>
      </section>

      <section className="learn-section">
        <div className="learn-section-heading">
          <h2>Bookshelf</h2>
          <p>Longer-form reading for people who want judgment, not just definitions.</p>
        </div>
        <div className="learn-book-grid">
          {books.map((book) => (
            <article key={book.title} className="learn-book-card">
              <p className="learn-book-author">{book.author}</p>
              <h3>{book.title}</h3>
              <p>{book.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="learn-section">
        <div className="learn-section-split">
          <div className="learn-split-block">
            <div className="learn-section-heading">
              <h2>Video Primers</h2>
              <p>Useful when you want a quicker, more visual entry point.</p>
            </div>
            <div className="learn-resource-grid">
              {videoPrimers.map((video) => (
                <ExternalResourceCard
                  key={video.title}
                  title={video.title}
                  detail={video.detail}
                  link={video.link}
                  format="Video"
                />
              ))}
            </div>
          </div>

          <div className="learn-split-block">
            <div className="learn-section-heading">
              <h2>Market Reference Sites</h2>
              <p>Good for checking prices, headlines, and broader market context during the day.</p>
            </div>
            <div className="learn-resource-grid">
              {marketSites.map((site) => (
                <ExternalResourceCard
                  key={site.title}
                  title={site.title}
                  detail={site.detail}
                  link={site.link}
                />
              ))}
            </div>
          </div>
        </div>
      </section>
    </TradingLayout>
  );
}

export default Learn;
