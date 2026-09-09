import colors from "../../../design-system/theme/colors";

export default function BadActorsTable({ badActors = [], onNavigate }) {
  if (!badActors || badActors.length === 0) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: colors.textMuted }}>
        No repeat bad actor pumps found in selected scope.
      </div>
    );
  }

  const handleDrilldown = (pumpTag) => {
    if (onNavigate) {
      onNavigate("history", { assetTag: pumpTag });
    }
  };

  return (
    <div style={{ width: "100%", overflowX: "auto" }} data-testid="bad-actors-table">
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem", textAlign: "left" }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${colors.border}`, color: colors.textMuted }}>
            <th style={{ padding: "8px 10px", fontWeight: 600 }}>Pump Tag</th>
            <th style={{ padding: "8px 10px", fontWeight: 600 }}>Area</th>
            <th style={{ padding: "8px 10px", fontWeight: 600 }}>Type</th>
            <th style={{ padding: "8px 10px", fontWeight: 600 }}>API Plan</th>
            <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "center" }}>Leaks</th>
            <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "center" }}>Readings</th>
            <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "center" }}>PMs</th>
            <th style={{ padding: "8px 10px", fontWeight: 600 }}>Latest Leak</th>
            <th style={{ padding: "8px 10px", fontWeight: 600, textAlign: "right" }}>Drilldown</th>
          </tr>
        </thead>
        <tbody>
          {badActors.map((pump) => {
            const hasRepeatLeaks = pump.leak_count > 1;
            return (
              <tr
                key={pump.pump_tag}
                style={{
                  borderBottom: `1px solid rgba(255,255,255,0.05)`,
                  transition: "background 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                <td style={{ padding: "8px 10px" }}>
                  <button
                    type="button"
                    onClick={() => handleDrilldown(pump.pump_tag)}
                    style={{
                      background: "none",
                      border: "none",
                      color: colors.info,
                      fontWeight: 700,
                      cursor: "pointer",
                      padding: 0,
                      textAlign: "left",
                    }}
                    title={`Open Equipment360 for ${pump.pump_tag}`}
                  >
                    {pump.pump_tag}
                  </button>
                </td>
                <td style={{ padding: "8px 10px", color: colors.text }}>{pump.area}</td>
                <td style={{ padding: "8px 10px", color: colors.textMuted }}>{pump.pump_type || "—"}</td>
                <td style={{ padding: "8px 10px", color: colors.textMuted }}>{pump.api_plan || "—"}</td>
                <td style={{ padding: "8px 10px", textAlign: "center" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: "10px",
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      background: hasRepeatLeaks ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      color: hasRepeatLeaks ? colors.danger : colors.warning,
                    }}
                  >
                    {pump.leak_count}
                  </span>
                </td>
                <td style={{ padding: "8px 10px", textAlign: "center", color: colors.textMuted }}>
                  {pump.cmon_readings}
                </td>
                <td style={{ padding: "8px 10px", textAlign: "center", color: colors.textMuted }}>
                  {pump.pm_count}
                </td>
                <td style={{ padding: "8px 10px", color: colors.textMuted }}>
                  {pump.latest_leak_date || "—"}
                </td>
                <td style={{ padding: "8px 10px", textAlign: "right" }}>
                  <button
                    type="button"
                    onClick={() => handleDrilldown(pump.pump_tag)}
                    style={{
                      background: "rgba(59, 130, 246, 0.1)",
                      border: `1px solid ${colors.info}`,
                      color: colors.info,
                      borderRadius: "4px",
                      padding: "3px 8px",
                      fontSize: "0.7rem",
                      cursor: "pointer",
                    }}
                  >
                    Inspect 360 →
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

