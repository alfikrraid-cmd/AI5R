import colors from "../../../design-system/theme/colors";

export default function HistoricalFindingsFeed({ findings = [], onNavigate }) {
  if (!findings || findings.length === 0) {
    return (
      <div style={{ padding: "20px", textAlign: "center", color: colors.textMuted, fontSize: "0.8rem" }}>
        No field leak findings recorded in selected scope.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        maxHeight: "360px",
        overflowY: "auto",
        paddingRight: "4px",
      }}
      data-testid="historical-findings-feed"
    >
      {findings.map((f, idx) => {
        const hasLeak = f.leak_de || f.leak_nde;
        return (
          <div
            key={`${f.pump_tag}-${idx}`}
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: `1px solid ${colors.border}`,
              borderRadius: "6px",
              padding: "10px 12px",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              fontSize: "0.75rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => onNavigate?.("history", { assetTag: f.pump_tag })}
                style={{
                  background: "none",
                  border: "none",
                  color: colors.info,
                  fontWeight: 700,
                  fontSize: "0.8rem",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                {f.pump_tag}
              </button>
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                {hasLeak && (
                  <span
                    style={{
                      background: "rgba(239, 68, 68, 0.15)",
                      color: colors.danger,
                      padding: "1px 6px",
                      borderRadius: "4px",
                      fontWeight: 600,
                      fontSize: "0.65rem",
                    }}
                  >
                    LEAK OBSERVATION
                  </span>
                )}
                <span style={{ color: colors.textMuted }}>{f.detected_date}</span>
              </div>
            </div>

            <p style={{ margin: 0, color: colors.text, fontStyle: "italic", lineHeight: "1.3" }}>
              "{f.remarks || "No specific engineering remark logged."}"
            </p>

            <div style={{ display: "flex", gap: "12px", color: colors.textMuted, fontSize: "0.7rem", marginTop: "2px" }}>
              {f.api_plan && <span>API Plan: {f.api_plan}</span>}
              {f.pump_type && <span>Pump Type: {f.pump_type}</span>}
              {f.follow_up_date && f.follow_up_date !== "-" && (
                <span style={{ color: colors.warning }}>Follow-up: {f.follow_up_date}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

