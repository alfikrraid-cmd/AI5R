import colors from "../../../design-system/theme/colors";

function renderMetricValue(val, suffix = "") {
  if (val === null || val === undefined) {
    return <span style={{ color: colors.textMuted }}>N/A</span>;
  }
  return (
    <span>
      {typeof val === "number" ? val.toLocaleString() : val}
      {suffix}
    </span>
  );
}

export default function AnalyticsKpiStrip({
  kpis = {},
  healthScore,
  criticalSpareCount,
}) {
  // Row 1: Primary Engineering KPI Strip (6 cards)
  const primaryCards = [
    {
      title: "Fleet Health",
      value: renderMetricValue(healthScore !== undefined && healthScore !== null ? healthScore : kpis.fleet_health, "%"),
      subtitle: healthScore ? "Reliability index" : "Fleet condition",
      color: healthScore >= 80 ? colors.success : colors.info,
      testId: "kpi-fleet-health",
    },
    {
      title: "Total Pumps",
      value: renderMetricValue(kpis.total_pumps),
      subtitle: kpis.active_pumps !== null && kpis.active_pumps !== undefined ? `${kpis.active_pumps} active` : "Fleet scope",
      color: colors.info,
      testId: "kpi-total-pumps",
    },
    {
      title: "Active Leak / Abnormal Finding",
      value: renderMetricValue(kpis.confirmed_seal_leaks),
      subtitle: `${kpis.de_leaks ?? 0} DE · ${kpis.nde_leaks ?? 0} NDE`,
      color: (kpis.confirmed_seal_leaks ?? 0) > 0 ? colors.danger : colors.success,
      testId: "kpi-confirmed-leaks",
    },
    {
      title: "PM Due",
      value: renderMetricValue(kpis.pm_scheduled_count ?? kpis.pm_due ?? kpis.pm_executed_count ?? kpis.pm_done_count),
      subtitle: kpis.pm_scheduled_count ? `${kpis.pm_scheduled_count} scheduled` : `${kpis.pm_executed_count ?? kpis.pm_done_count ?? 0} executed`,
      color: colors.success,
      testId: "kpi-pm-executed",
    },
    {
      title: "PM Overdue",
      value: renderMetricValue(kpis.pm_overdue !== undefined && kpis.pm_overdue !== null ? kpis.pm_overdue : (kpis.pm_compliance_percent !== null && kpis.pm_compliance_percent !== undefined ? 0 : null)),
      subtitle: kpis.pm_compliance_percent !== null && kpis.pm_compliance_percent !== undefined ? `${kpis.pm_compliance_percent}% compliance` : "Compliance: N/A",
      color: (kpis.pm_overdue ?? 0) > 0 ? colors.danger : colors.textMuted,
      testId: "kpi-pm-compliance",
    },
    {
      title: "Critical Spare",
      value: renderMetricValue(criticalSpareCount !== undefined && criticalSpareCount !== null ? criticalSpareCount : kpis.critical_spare_count),
      subtitle: "Stock availability",
      color: (criticalSpareCount ?? 0) > 0 ? colors.info : colors.textMuted,
      testId: "kpi-critical-spare",
    },
  ];

  // Secondary line: Monitored, Breakdowns, and MTBF/MTTR (strictly disclosed as N/A when data absent)
  const secondaryMetrics = [
    {
      label: "Monitored Pumps",
      value: renderMetricValue(kpis.monitored_pumps),
      testId: "kpi-monitored-pumps",
    },
    {
      label: "Breakdowns",
      value: renderMetricValue(kpis.breakdown_count),
      testId: "kpi-breakdowns",
    },
    {
      label: "Fleet MTBF",
      value: renderMetricValue(kpis.fleet_mtbf_days, " d"),
      testId: "kpi-fleet-mtbf",
      note: "Requires ≥2 failure events",
    },
    {
      label: "Fleet MTTR",
      value: renderMetricValue(kpis.fleet_mttr_hours, " h"),
      testId: "kpi-fleet-mttr",
      note: "Requires ≥2 failure events",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }} data-testid="analytics-kpi-strip">
      {/* Primary 6 Cards Strip */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "12px",
        }}
      >
        {primaryCards.map((c) => (
          <div
            key={c.title}
            data-testid={c.testId}
            style={{
              background: colors.panel,
              border: `1px solid ${colors.border}`,
              borderRadius: "8px",
              padding: "10px 14px",
              display: "flex",
              flexDirection: "column",
              gap: "2px",
            }}
          >
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                color: colors.textMuted,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {c.title}
            </span>
            <div style={{ fontSize: "1.35rem", fontWeight: 700, color: c.color, lineHeight: "1.2" }}>
              {c.value}
            </div>
            <span style={{ fontSize: "0.68rem", color: colors.textMuted }}>
              {c.subtitle}
            </span>
          </div>
        ))}
      </div>

      {/* Secondary Compact Reliability Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "20px",
          padding: "6px 14px",
          background: "rgba(255, 255, 255, 0.02)",
          border: `1px solid ${colors.border}`,
          borderRadius: "6px",
          fontSize: "0.75rem",
          color: colors.textMuted,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 600, color: colors.text, fontSize: "0.72rem", textTransform: "uppercase" }}>
          Fleet Reliability Diagnostics:
        </span>
        {secondaryMetrics.map((m) => (
          <div key={m.label} data-testid={m.testId} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>{m.label}:</span>
            <strong style={{ color: colors.text }}>{m.value}</strong>
            {m.note && <span style={{ fontSize: "0.65rem", color: colors.textMuted }}>({m.note})</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
