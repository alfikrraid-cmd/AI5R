import { useMemo, useState } from "react";
import colors from "../../../../design-system/theme/colors";

export default function HorizontalBarChart({
  data = [],
  labelKey = "pump_tag",
  valueKey = "leak_count",
  secondaryKey = "cmon_readings",
  categoryKey = "area",
  title = "Top Risk Pumps",
  onSelect,
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  const { items, maxVal } = useMemo(() => {
    if (!data || data.length === 0) return { items: [], maxVal: 5 };
    const slice = data.slice(0, 7);
    let max = 1;
    for (const item of slice) {
      const v = Number(item[valueKey]) || 0;
      if (v > max) max = v;
    }
    return { items: slice, maxVal: max };
  }, [data, valueKey]);

  if (!data || data.length === 0) {
    return (
      <div
        style={{ padding: "32px", textAlign: "center", color: colors.textMuted }}
        data-testid="horizontal-bar-chart"
      >
        No risk/bad actor records identified in selected scope.
      </div>
    );
  }

  return (
    <div
      style={{ width: "100%", display: "flex", flexDirection: "column", gap: "12px" }}
      data-testid="horizontal-bar-chart"
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: colors.text }}>{title}</span>
        <span style={{ fontSize: "0.75rem", color: colors.textMuted }}>Ranked by Incidents</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {items.map((item, idx) => {
          const val = Number(item[valueKey]) || 0;
          const label = item[labelKey] || item.tag_number || "Unknown";
          const cat = item[categoryKey] || "";
          const secondary = item[secondaryKey] !== undefined ? item[secondaryKey] : null;
          const pct = Math.max(8, Math.round((val / maxVal) * 100));
          const isHovered = hoveredIdx === idx;

          return (
            <div
              key={label}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "4px",
                padding: "6px 8px",
                borderRadius: "6px",
                background: isHovered ? "rgba(255, 255, 255, 0.04)" : "transparent",
                transition: "background 0.15s ease",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => onSelect?.(label)}
                    style={{
                      background: "none",
                      border: "none",
                      color: colors.info,
                      fontWeight: 700,
                      cursor: "pointer",
                      padding: 0,
                      textAlign: "left",
                    }}
                    title={`Inspect Equipment360 for ${label}`}
                  >
                    {label}
                  </button>
                  {cat && (
                    <span
                      style={{
                        fontSize: "0.7rem",
                        padding: "1px 6px",
                        borderRadius: "4px",
                        background: "rgba(255,255,255,0.06)",
                        color: colors.textMuted,
                      }}
                    >
                      {cat}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {secondary !== null && (
                    <span style={{ fontSize: "0.7rem", color: colors.textMuted }}>
                      {secondary} readings
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: val > 1 ? colors.danger : colors.warning,
                      background: val > 1 ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      padding: "1px 8px",
                      borderRadius: "10px",
                    }}
                  >
                    {val} {val === 1 ? "leak" : "leaks"}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div
                style={{
                  width: "100%",
                  height: "8px",
                  background: "rgba(255, 255, 255, 0.06)",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    background: val > 1 ? `linear-gradient(90deg, ${colors.warning}, ${colors.danger})` : colors.warning,
                    borderRadius: "4px",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
