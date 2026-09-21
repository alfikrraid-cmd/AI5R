import { useMemo, useState } from "react";
import colors from "../../../../design-system/theme/colors";

const WIDTH = 640;
const HEIGHT = 240;
const PAD = { top: 24, right: 24, bottom: 50, left: 48 };

export default function BarChart({
  data = [],
  categoryKey = "area",
  bars = [
    { key: "seal_leaks", label: "Leaks", color: colors.danger },
    { key: "pm_count", label: "PMs", color: colors.success },
  ],
  title = "Area Comparison",
  stacked = false,
  onSelectCategory,
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  const { items, maxY, xStep, barWidth, plotHeight, plotWidth } = useMemo(() => {
    if (!data || data.length === 0) {
      return { items: [], maxY: 10, xStep: 0, barWidth: 0, plotHeight: 0, plotWidth: 0 };
    }

    // Slice to top 8 items max so bars remain legible
    const topData = data.slice(0, 8);

    let maxVal = 0;
    for (const item of topData) {
      if (stacked) {
        const sumVal = bars.reduce((acc, bar) => acc + (Number(item[bar.key]) || 0), 0);
        if (sumVal > maxVal) maxVal = sumVal;
      } else {
        for (const bar of bars) {
          const val = Number(item[bar.key]) || 0;
          if (val > maxVal) maxVal = val;
        }
      }
    }
    const safeMax = maxVal > 0 ? Math.ceil(maxVal * 1.15) : 5;

    const pWidth = WIDTH - PAD.left - PAD.right;
    const pHeight = HEIGHT - PAD.top - PAD.bottom;
    const step = pWidth / topData.length;
    const bWidth = stacked
      ? Math.max(12, Math.min(36, step * 0.5))
      : Math.max(6, Math.min(24, (step * 0.7) / bars.length));

    return {
      items: topData,
      maxY: safeMax,
      xStep: step,
      barWidth: bWidth,
      plotHeight: pHeight,
      plotWidth: pWidth,
    };
  }, [data, bars, stacked]);

  if (!data || data.length === 0) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: colors.textMuted }}>
        No category records available for selected scope.
      </div>
    );
  }

  const yTicks = [0, Math.round(maxY / 2), maxY];

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "10px" }} data-testid="bar-chart">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: colors.text }}>{title}</span>
        <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "0.75rem" }}>
          {bars.map((b) => (
            <div key={b.key} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: b.color }} />
              <span style={{ color: colors.textMuted }}>{b.label}</span>
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
          {/* Y Grid lines and values */}
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

          {/* X Baseline */}
          <line
            x1={PAD.left}
            y1={HEIGHT - PAD.bottom}
            x2={WIDTH - PAD.right}
            y2={HEIGHT - PAD.bottom}
            stroke={colors.border}
            strokeWidth="1"
          />

          {/* Bar groups */}
          {items.map((item, idx) => {
            const groupCenterX = PAD.left + idx * xStep + xStep / 2;
            const totalGroupWidth = bars.length * barWidth + (bars.length - 1) * 4;
            const groupStartX = groupCenterX - totalGroupWidth / 2;
            const labelText = String(item[categoryKey] ?? "N/A");

            let currentStackedY = PAD.top + plotHeight;
            const stackedBarX = groupCenterX - barWidth / 2;

            return (
              <g
                key={`group-${idx}`}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                onClick={() => onSelectCategory?.(labelText)}
                style={{ cursor: onSelectCategory ? "pointer" : "default" }}
              >
                {/* Category Label */}
                <text
                  x={groupCenterX}
                  y={HEIGHT - PAD.bottom + 18}
                  textAnchor="middle"
                  fill={hoveredIndex === idx ? colors.info : colors.textMuted}
                  fontSize="10"
                  fontWeight={hoveredIndex === idx ? "700" : "400"}
                >
                  {labelText.length > 9 ? `${labelText.slice(0, 8)}…` : labelText}
                </text>

                {/* Individual or stacked bars */}
                {bars.map((bar, bIdx) => {
                  const val = Number(item[bar.key]) || 0;
                  const bHeight = maxY > 0 ? (val / maxY) * plotHeight : 0;
                  
                  if (stacked) {
                    if (val === 0) return null;
                    currentStackedY -= bHeight;
                    return (
                      <rect
                        key={`bar-${idx}-${bIdx}`}
                        x={stackedBarX}
                        y={currentStackedY}
                        width={barWidth}
                        height={Math.max(bHeight, 2)}
                        rx="1"
                        fill={bar.color}
                        opacity={hoveredIndex === null || hoveredIndex === idx ? 1 : 0.4}
                        style={{ transition: "opacity 0.2s ease" }}
                      />
                    );
                  }

                  const bX = groupStartX + bIdx * (barWidth + 4);
                  const bY = PAD.top + plotHeight - bHeight;

                  return (
                    <rect
                      key={`bar-${idx}-${bIdx}`}
                      x={bX}
                      y={bY}
                      width={barWidth}
                      height={Math.max(bHeight, 2)}
                      rx="3"
                      fill={bar.color}
                      opacity={hoveredIndex === null || hoveredIndex === idx ? 1 : 0.4}
                      style={{ transition: "opacity 0.2s ease, transform 0.2s ease" }}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>

        {/* Tooltip on hover */}
        {hoveredIndex !== null && items[hoveredIndex] && (
          <div
            style={{
              position: "absolute",
              top: "10px",
              left: Math.min(
                Math.max(PAD.left + hoveredIndex * xStep - 40, 10),
                WIDTH - 150
              ),
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
              {items[hoveredIndex][categoryKey]}
            </div>
            {bars.map((b) => (
              <div key={b.key} style={{ display: "flex", justifyContent: "space-between", gap: "12px", color: b.color }}>
                <span>{b.label}:</span>
                <span style={{ fontWeight: 700 }}>{items[hoveredIndex][b.key] ?? 0}</span>
              </div>
            ))}
            {stacked && (
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", color: colors.text, marginTop: "4px", borderTop: `1px solid ${colors.border}`, paddingTop: "4px" }}>
                <span>Total:</span>
                <span style={{ fontWeight: 700 }}>{bars.reduce((sum, b) => sum + (Number(items[hoveredIndex][b.key]) || 0), 0)}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
