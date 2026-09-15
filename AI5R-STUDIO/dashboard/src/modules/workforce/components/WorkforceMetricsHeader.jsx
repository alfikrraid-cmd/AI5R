import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function WorkforceMetricsHeader({ metrics = {} }) {
  const cards = [
    {
      id: "total_employees",
      label: "Total Employees",
      value: metrics.total_employees ?? 9,
      color: colors.info,
      sublabel: `${metrics.active_employees ?? 9} Active`,
    },
    {
      id: "available_employees",
      label: "Available",
      value: metrics.available_employees ?? 0,
      color: colors.success,
      sublabel: "Ready for tasks",
    },
    {
      id: "working_employees",
      label: "Working",
      value: metrics.working_employees ?? 0,
      color: colors.purple,
      sublabel: "Executing / Thinking",
    },
    {
      id: "waiting_approval",
      label: "Waiting Approval",
      value: metrics.waiting_approval_employees ?? metrics.pending_approvals ?? 0,
      color: colors.warning,
      sublabel: "Chief Gate Pending",
    },
    {
      id: "total_tasks",
      label: "Work Items",
      value: metrics.total_tasks ?? 0,
      color: colors.text,
      sublabel: `${metrics.completed_tasks ?? 0} Completed`,
    },
    {
      id: "uptime",
      label: "Workforce State",
      value: metrics.uptime ?? "OPERATIONAL",
      color: colors.success,
      sublabel: "Autonomous Loop",
    },
  ];

  return (
    <div
      data-testid="workforce-metrics-header"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: spacing.md,
        marginBottom: spacing.lg,
      }}
    >
      {cards.map((card) => (
        <div
          key={card.id}
          data-testid={`metric-card-${card.id}`}
          style={{
            background: colors.panel,
            padding: `${spacing.md}px`,
            borderRadius: spacing.sm,
            borderLeft: `4px solid ${card.color}`,
            display: "flex",
            flexDirection: "column",
            gap: spacing.xs,
          }}
        >
          <span
            style={{
              fontSize: typography.size.xs,
              color: colors.textMuted,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              fontWeight: typography.weight.bold,
            }}
          >
            {card.label}
          </span>
          <span
            style={{
              fontSize: typography.size.xxl,
              fontWeight: typography.weight.bold,
              color: card.color,
              lineHeight: 1.1,
            }}
          >
            {card.value}
          </span>
          <span
            style={{
              fontSize: typography.size.xs,
              color: colors.textMuted,
            }}
          >
            {card.sublabel}
          </span>
        </div>
      ))}
    </div>
  );
}

