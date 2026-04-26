export default function SimpleLineChart({ userSeries = [], modelSeries = [], labels = [] }) {
  const width = 960;
  const height = 320;
  const padding = 28;
  const plotLength = Math.max(labels.length, userSeries.length, modelSeries.length);
  const allValues = [...userSeries, ...modelSeries].filter(
    (value) => typeof value === "number" && Number.isFinite(value)
  );

  if (allValues.length < 2) {
    return <div className="empty-state">More confirmed trading days are needed before the comparison chart becomes useful.</div>;
  }

  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const span = max - min || 1;

  const buildPoints = (series) =>
    series
      .map((value, index) => {
        if (typeof value !== "number" || !Number.isFinite(value)) {
          return null;
        }
        const x = padding + (index / Math.max(plotLength - 1, 1)) * (width - padding * 2);
        const y = height - padding - ((value - min) / span) * (height - padding * 2);
        return `${x},${y}`;
      })
      .filter(Boolean)
      .join(" ");

  const yTicks = Array.from({ length: 4 }).map((_, idx) => {
    const value = min + (span / 3) * idx;
    const y = height - padding - ((value - min) / span) * (height - padding * 2);
    return { value, y };
  });

  const labelStep = Math.max(1, Math.floor(labels.length / 4));

  return (
    <div className="chart-card">
      <svg viewBox={`0 0 ${width} ${height}`} className="portfolio-chart" role="img">
        {yTicks.map((tick) => (
          <g key={tick.y}>
            <line x1={padding} x2={width - padding} y1={tick.y} y2={tick.y} className="chart-grid" />
            <text x={8} y={tick.y + 4} className="chart-axis-text">
              ${tick.value.toFixed(0)}
            </text>
          </g>
        ))}
        <polyline fill="none" stroke="#2dd4bf" strokeWidth="3" points={buildPoints(userSeries)} />
        <polyline
          fill="none"
          stroke="#94a3b8"
          strokeWidth="3"
          strokeDasharray="10 8"
          points={buildPoints(modelSeries)}
        />
        {labels
          .map((label, index) => ({ label, index }))
          .filter(({ index }) => index % labelStep === 0 || index === labels.length - 1)
          .map(({ label, index }) => {
            const x = padding + (index / Math.max(labels.length - 1, 1)) * (width - padding * 2);
            return (
              <text key={`${label}-${x}`} x={x} y={height - 6} className="chart-axis-text" textAnchor="middle">
                {label}
              </text>
            );
          })}
      </svg>
      <div className="chart-legend">
        <span>
          <i className="legend-swatch user" />
          Your Portfolio
        </span>
        <span>
          <i className="legend-swatch model" />
          Model Portfolio
        </span>
      </div>
    </div>
  );
}
