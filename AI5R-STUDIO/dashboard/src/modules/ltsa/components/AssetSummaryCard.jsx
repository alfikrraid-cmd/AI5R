import { Badge, Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { criticalityBadgeVariant, statusBadgeVariant } from "../utils/pumpHealth";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function AssetSummaryCard({ summary }) {
  return (
    <Card title="Asset Summary">
      <Field label="Pump" value={summary.pump} />
      <Field label="Tag" value={summary.tag} />
      <Field label="Area" value={summary.area} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
        <Badge variant={statusBadgeVariant(summary.status)}>{summary.status}</Badge>
      </div>

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Criticality</div>
        <Badge variant={criticalityBadgeVariant(summary.criticality)}>{summary.criticality}</Badge>
      </div>

      <Field
        label="Last Preventive Maintenance"
        value={summary.lastPreventiveMaintenance ?? "None recorded"}
      />
      <Field
        label="Last Corrective Maintenance"
        value={summary.lastCorrectiveMaintenance ?? "None recorded"}
      />
      <Field label="Open Work Orders" value={summary.openWorkOrders} />
      <Field label="Last Activity" value={summary.lastActivity ?? "No recorded activity"} />
    </Card>
  );
}
