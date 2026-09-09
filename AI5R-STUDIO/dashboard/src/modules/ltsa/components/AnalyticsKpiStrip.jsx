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

export default function AnalyticsKpiStrip({ kpis = {} }) {
  const cards = [
    {
      title: "Total Pumps",
      value: renderMetricValue(kpis.total_pumps),
      subtitle: kpis.active_pumps !== null && kpis.active_pumps !== undefined ? `${kpis.active_pumps} active` : "Fleet scope",
      color: colors.info,
      testId: "kpi-total-pumps",
    },
    {
      title: "Monitored Pumps",
      value: renderMetricValue(kpis.monitored_pumps),
      subtitle: "Active CM logging",
      color: colors.purple,
      testId: "kpi-monitored-pumps",
    },
    {
      title: "PM Executed",
      value: renderMetricValue(kpis.pm_executed_count),
      subtitle: `${kpis.pm_done_count ?? 0} Completed`,
      color: colors.success,
      testId: "kpi-pm-executed",
    },
    {
      title: "PM Compliance",
      value: renderMetricValue(kpis.pm_compliance_percent, "%"),
      subtitle: kpis.pm_scheduled_count ? `${kpis.pm_scheduled_count} scheduled` : "No schedule target",
      color: kpis.pm_compliance_percent !== null ? colors.success : colors.textMuted,
      testId: "kpi-pm-compliance",
    },
    {
      title: "Confirmed Leaks",
      value: renderMetricValue(kpis.confirmed_seal_leaks),
      subtitle: `${kpis.de_leaks ?? 0} DE · ${kpis.nde_leaks ?? 0} NDE`,
      color: (kpis.confirmed_seal_leaks ?? 0) > 0 ? colors.danger : colors.success,
      testId: "kpi-confirmed-leaks",
    },
    {
      title: "Breakdowns",
      value: renderMetricValue(kpis.breakdown_count),
      subtitle: "0 reported failures",
      color: colors.info,
      testId: "kpi-breakdowns",
    },
    {
      title: "Fleet MTBF",
      value: renderMetricValue(kpis.fleet_mtbf_days, " d"),
      subtitle: "Requires ≥2 failure events",
      color: colors.textMuted,
      testId: "kpi-fleet-mtbf",
    },
    {
      title: "Fleet MTTR",
      value: renderMetricValue(kpis.fleet_mttr_hours, " h"),
      subtitle: "Requires ≥2 failure events",
      color: colors.textMuted,
      testId: "kpi-fleet-mttr",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: "12px",
        marginBottom: "16px",
      }}
      data-testid="analytics-kpi-strip"
    >
      {cards.map((c) => (
        <div
          key={c.title}
          data-testid={c.testId}
          style={{
            background: colors.panel,
            border: `1px solid ${colors.border}`,
            borderRadius: "8px",
            padding: "12px 14px",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <span style={{ fontSize: "0.7rem", fontWeight: 600, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {c.title}
          </span>
          <div style={{ fontSize: "1.4rem", fontWeight: 700, color: c.color, lineHeight: "1.2" }}>
            {c.value}
          </div>
          <span style={{ fontSize: "0.7rem", color: colors.textMuted }}>
            {c.subtitle}
          </span>
        </div>
      ))}
    </div>
  );
}

