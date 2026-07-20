import { Badge, Card, ProgressBar } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { statusBadgeVariant, statusLabel } from "../utils/cmStatus";

export default function MaintenanceHealthPanel({ health }) {
  return (
    <Card title="Maintenance Health">
      <div style={{ marginBottom: spacing.md }}>
        <ProgressBar
          value={health.pmComplianceRate}
          max={100}
          label={`PM Compliance — ${health.pmComplianceRate}% (${health.totalPM - health.overduePM} of ${health.totalPM} not overdue)`}
        />
      </div>

      <div style={{ marginBottom: spacing.md }}>
        <ProgressBar
          value={health.closedWorkOrders}
          max={health.totalWorkOrders}
          label={`Work Orders — ${health.closedWorkOrders} closed / ${health.openWorkOrders} open (of ${health.totalWorkOrders})`}
        />
      </div>

      <div>
        <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
          Corrective Maintenance Status
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
          {Object.entries(health.cmStatusCounts).map(([status, count]) => (
            <Badge key={status} variant={statusBadgeVariant(status)}>
              {statusLabel(status)}: {count}
            </Badge>
          ))}
        </div>
      </div>
    </Card>
  );
}
