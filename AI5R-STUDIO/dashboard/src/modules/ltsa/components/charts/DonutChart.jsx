import { useMemo, useState } from "react";
import colors from "../../../../design-system/theme/colors";

const SIZE = 200;
const STROKE_WIDTH = 28;
const RADIUS = (SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const PALETTE = [
  colors.danger,
  colors.info,
  colors.warning,
  colors.purple,
  colors.success,
  "#06B6D4",
  "#F97316",
];

export default function DonutChart({
  data = [],
  labelKey = "label",
  valueKey = "value",
  title = "Distribution",
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  const { slices, total } = useMemo(() => {
    if (!data || data.length === 0) {
      return { slices: [], total: 0 };
    }

    const totalVal = data.reduce((acc, cur) => acc + (Number(cur[valueKey]) || 0), 0);
    if (totalVal === 0) {
      return { slices: [], total: 0 };
    }

    let currentOffset = 0;
    const computedSlices = data.map((d, idx) => {
      const val = Number(d[valueKey]) || 0;
      const pct = val / totalVal;
      const strokeLength = pct * CIRCUMFERENCE;
      const strokeDasharray = `${strokeLength} ${CIRCUMFERENCE - strokeLength}`;
      const strokeDashoffset = -currentOffset;
      currentOffset += strokeLength;

      return {
        ...d,
        color: d.color || PALETTE[idx % PALETTE.length],
        pct: Math.round(pct * 100),
        strokeDasharray,
        strokeDashoffset,
        val,
      };
    });

    return { slices: computedSlices, total: totalVal };
  }, [data, valueKey]);

  if (!data || data.length === 0 || total === 0) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: colors.textMuted }}>
        No distribution data available.
      </div>
    );
  }

  const activeSlice = hoveredIndex !== null ? slices[hoveredIndex] : null;

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "12px" }} data-testid="donut-chart">
      {title && (
        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: colors.text }}>
          {title}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-around", flexWrap: "wrap", gap: "16px" }}>
        {/* Donut SVG */}
        <div style={{ position: "relative", width: SIZE, height: SIZE, flexShrink: 0 }}>
          <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            style={{ transform: "rotate(-90deg)", overflow: "visible" }}
            role="img"
            aria-label={title}
          >
            {/* Background ring */}
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke={colors.border}
              strokeWidth={STROKE_WIDTH}
            />

            {/* Slices */}
            {slices.map((slice, idx) => (
              <circle
                key={`slice-${idx}`}
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke={slice.color}
                strokeWidth={hoveredIndex === idx ? STROKE_WIDTH + 4 : STROKE_WIDTH}
                strokeDasharray={slice.strokeDasharray}
                strokeDashoffset={slice.strokeDashoffset}
                strokeLinecap="butt"
                style={{ cursor: "pointer", transition: "stroke-width 0.2s ease, opacity 0.2s ease" }}
                opacity={hoveredIndex === null || hoveredIndex === idx ? 1 : 0.4}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            ))}
          </svg>

          {/* Center text */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              pointerEvents: "none",
              textAlign: "center",
            }}
          >
            <span style={{ fontSize: "1.25rem", fontWeight: 700, color: colors.text }}>
              {activeSlice ? activeSlice.val : total}
            </span>
            <span style={{ fontSize: "0.7rem", color: colors.textMuted }}>
              {activeSlice ? `${activeSlice[labelKey]} (${activeSlice.pct}%)` : "Total Events"}
            </span>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxWidth: "200px" }}>
          {slices.map((s, idx) => (
            <div
              key={`legend-${idx}`}
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "10px",
                fontSize: "0.75rem",
                cursor: "pointer",
                padding: "2px 4px",
                borderRadius: "4px",
                background: hoveredIndex === idx ? "rgba(255,255,255,0.05)" : "transparent",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: s.color, flexShrink: 0 }} />
                <span style={{ color: colors.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {s[labelKey]}
                </span>
              </div>
              <span style={{ fontWeight: 600, color: colors.textMuted }}>{s.val}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
