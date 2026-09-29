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
    </Card>
  );
}
