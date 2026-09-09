import { useMemo, useState } from "react";
import colors from "../../../../design-system/theme/colors";

const WIDTH = 640;
const HEIGHT = 240;
const PAD = { top: 24, right: 24, bottom: 44, left: 48 };

function formatDateLabel(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    return `${d.getDate()} ${d.toLocaleString("en-US", { month: "short" })}`;
  } catch {
    return dateStr;
  }
}

export default function TimeSeriesChart({
  data = [],
  series = [
    { key: "seal_leaks", label: "Seal Leaks", color: colors.danger },
    { key: "pm_count", label: "PM Done", color: colors.success },
    { key: "cmon_readings", label: "CM Readings", color: colors.info },
  ],
  title = "Operational Activity & Incidents Trend",
}) {
  const [activePoint, setActivePoint] = useState(null);

  const { pointsBySeries, xTicks, yTicks, maxY } = useMemo(() => {
    if (!data || data.length === 0) {
      return { pointsBySeries: {}, xTicks: [], yTicks: [0, 5, 10], maxY: 10 };
    }

    // Find max Y across all active series
    let computedMax = 0;
    for (const d of data) {
      for (const s of series) {
        const val = Number(d[s.key]) || 0;
        if (val > computedMax) computedMax = val;
      }
    }
    const safeMax = computedMax > 0 ? Math.ceil(computedMax * 1.15) : 5;

    const plotWidth = WIDTH - PAD.left - PAD.right;
    const plotHeight = HEIGHT - PAD.top - PAD.bottom;
    const n = data.length;

    const scaledSeries = {};
    for (const s of series) {
      scaledSeries[s.key] = data.map((d, i) => {
        const x = n > 1 ? PAD.left + (i / (n - 1)) * plotWidth : PAD.left + plotWidth / 2;
        const val = Number(d[s.key]) || 0;
        const y = PAD.top + plotHeight - (val / safeMax) * plotHeight;
        return { x, y, value: val, date: d.date, raw: d };
      });
    }

    // Pick 4-6 x-axis ticks
    const step = Math.max(1, Math.floor(n / 5));
    const ticks = [];
    for (let i = 0; i < n; i += step) {
      ticks.push({ index: i, date: data[i].date, x: n > 1 ? PAD.left + (i / (n - 1)) * plotWidth : PAD.left + plotWidth / 2 });
    }
    if (n > 1 && ticks[ticks.length - 1].index !== n - 1) {
      ticks.push({ index: n - 1, date: data[n - 1].date, x: PAD.left + plotWidth });
    }

    const yValues = [0, Math.round(safeMax / 2), safeMax];

    return { pointsBySeries: scaledSeries, xTicks: ticks, yTicks: yValues, maxY: safeMax };
  }, [data, series]);

  if (!data || data.length === 0) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: colors.textMuted }}>
        No trend records available for selected period.
      </div>
    );
  }

  const plotHeight = HEIGHT - PAD.top - PAD.bottom;

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "10px" }} data-testid="timeseries-chart">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: colors.text }}>{title}</span>
        <div style={{ display: "flex", gap: "14px", alignItems: "center", fontSize: "0.75rem" }}>
          {series.map((s) => (
            <div key={s.key} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: s.color }} />
              <span style={{ color: colors.textMuted }}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ position: "relative", width: "100%" }}>
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          style={{ width: "100%", height: "auto", display: "block", overflow: "visible" }}
          role="img"
          aria-label={title}
        >
          {/* Grid lines and Y labels */}
          {yTicks.map((yVal) => {
            const yPos = PAD.top + plotHeight - (yVal / maxY) * plotHeight;
            return (
              <g key={`y-${yVal}`}>
                <line
                  x1={PAD.left}
                  y1={yPos}
                  x2={WIDTH - PAD.right}
                  y2={yPos}
                  stroke={colors.border}
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={PAD.left - 8}
                  y={yPos + 4}
                  textAnchor="end"
                  fill={colors.textMuted}
                  fontSize="10"
                >
                  {yVal}
                </text>
              </g>
            );
          })}

          {/* X axis lines & labels */}
          <line
            x1={PAD.left}
            y1={HEIGHT - PAD.bottom}
            x2={WIDTH - PAD.right}
            y2={HEIGHT - PAD.bottom}
            stroke={colors.border}
            strokeWidth="1"
          />
          {xTicks.map((tick) => (
            <g key={`x-${tick.index}`}>
              <line
                x1={tick.x}
                y1={HEIGHT - PAD.bottom}
                x2={tick.x}
                y2={HEIGHT - PAD.bottom + 4}
                stroke={colors.border}
                strokeWidth="1"
              />
              <text
                x={tick.x}
                y={HEIGHT - PAD.bottom + 18}
                textAnchor="middle"
                fill={colors.textMuted}
                fontSize="10"
              >
                {formatDateLabel(tick.date)}
              </text>
            </g>
          ))}

          {/* Series paths and points */}
          {series.map((s) => {
            const pts = pointsBySeries[s.key] || [];
            if (pts.length === 0) return null;

            const pathD = pts.reduce((acc, p, idx) => `${acc} ${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`, "");

            return (
              <g key={`series-${s.key}`}>
                <path
                  d={pathD}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {pts.map((p, idx) => (
                  <circle
                    key={`${s.key}-${idx}`}
                    cx={p.x}
                    cy={p.y}
                    r={activePoint?.index === idx ? "5" : "3"}
                    fill={s.color}
                    stroke={colors.panel}
                    strokeWidth="1.5"
                    style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                    onMouseEnter={() => setActivePoint({ index: idx, date: p.date, raw: p.raw, x: p.x, y: p.y })}
                    onMouseLeave={() => setActivePoint(null)}
                  />
                ))}
              </g>
            );
          })}

          {/* Active point indicator bar */}
          {activePoint && (
            <line
              x1={activePoint.x}
              y1={PAD.top}
              x2={activePoint.x}
              y2={HEIGHT - PAD.bottom}
              stroke={colors.textMuted}
              strokeWidth="1"
              strokeDasharray="2 2"
              pointerEvents="none"
            />
          )}
        </svg>

        {/* Hover Tooltip */}
        {activePoint && (
          <div
            style={{
              position: "absolute",
              top: "10px",
              left: Math.min(Math.max(activePoint.x - 60, 10), WIDTH - 160),
              background: colors.panel,
              border: `1px solid ${colors.border}`,
              borderRadius: "6px",
              padding: "8px 12px",
              boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              pointerEvents: "none",
              zIndex: 10,
              fontSize: "0.75rem",
            }}
          >
            <div style={{ fontWeight: 600, color: colors.text, marginBottom: "4px" }}>
              {formatDateLabel(activePoint.date)}
            </div>
            {series.map((s) => (
              <div key={s.key} style={{ display: "flex", justifyContent: "space-between", gap: "12px", color: s.color }}>
                <span>{s.label}:</span>
                <span style={{ fontWeight: 700 }}>{activePoint.raw[s.key] ?? 0}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

