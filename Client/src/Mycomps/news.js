import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TradingLayout from "./TradingLayout";
import "../stylesheets/news.css";

function News() {
  const [news, setNews] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    axios
      .get(
        'https://newsapi.org/v2/top-headlines?country=us&category=business&apiKey=7f9ff6642a614b9b8ee8bd3125a6d7a5'
      )
      .then((res) => {
        if (!mounted) return;
        setNews((res.data.articles || []).filter((item) => item.title && item.url));
      })
      .catch(() => {
        if (mounted) {
          setError("Unable to load market headlines right now.");
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const featuredStories = news.filter((item) => item.author || item.description);

  return (
    <TradingLayout
      title="News"
      subtitle="Business headlines and market stories that can help users interpret the broader backdrop around the ensemble's trade suggestions."
    >
      <div className="news-page">
        <section className="news-summary">
          <article className="news-callout">
            <p className="news-kicker">Market Context</p>
            <h2>Use headlines to understand the mood around the model, not to chase every move.</h2>
            <p>
              This page is meant to support judgment. Scan major business stories, spot themes in
              sentiment, and use them as context when you review daily recommendations.
            </p>
          </article>
          <div className="news-stat-grid">
            <article className="news-stat-card">
              <span className="news-stat-value">{featuredStories.length}</span>
              <span className="news-stat-label">Stories with enough detail to review</span>
            </article>
            <article className="news-stat-card">
              <span className="news-stat-value">US</span>
              <span className="news-stat-label">Business headline feed for the current build</span>
            </article>
          </div>
        </section>

        {loading ? <div className="empty-state">Loading market headlines...</div> : null}
        {!loading && error ? <div className="error-banner">{error}</div> : null}

        {!loading && !error ? (
          <section className="news-grid">
            {featuredStories.map((story, index) => (
              <article className="news-card" key={`${story.url}-${index}`}>
                <img
                  src={story.urlToImage || "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80"}
                  className="news-card-image"
                  alt={story.title || "Business news"}
                />
                <div className="news-card-body">
                  <div className="news-card-meta">
                    <span>{story.author || "Unknown author"}</span>
                    <span>{story.publishedAt ? new Date(story.publishedAt).toLocaleDateString() : "Recent"}</span>
                  </div>
                  <h3>{story.title}</h3>
                  <p>{story.description || "Open the full story for more detail."}</p>
                  <div className="news-card-footer">
                    <span className="news-source">{story.source?.name || "Business feed"}</span>
                    <a href={story.url} className="news-link" target="_blank" rel="noopener noreferrer">
                      Read Story
                    </a>
                  </div>
                </div>
              </article>
            ))}
          </section>
        ) : null}
      </div>
    </TradingLayout>
  );
}

export default News;
