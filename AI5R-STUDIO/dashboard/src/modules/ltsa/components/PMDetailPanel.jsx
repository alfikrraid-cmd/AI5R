import { Badge, Card, EmptyState, Timeline } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  frequencyBadgeVariant,
  frequencyLabel,
  statusBadgeVariant,
  statusLabel,
  triggerTypeLabel,
} from "../utils/pmStatus";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function PMDetailPanel({ pm }) {
  if (!pm) {
    return (
      <EmptyState
        title="No PM schedule selected"
        description="Select a PM schedule from the list to view its details."
      />
    );
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{pm.procedure}</h2>

      <Card title="PM Schedule Summary">
        <Field label="Equipment" value={pm.area ? `${pm.equipmentTag} — ${pm.area}` : pm.equipmentTag} />
        <Field label="Trigger Type" value={triggerTypeLabel(pm.triggerType)} />
        <Field label="Last Performed" value={pm.lastPerformed ?? "Not yet performed"} />
        <Field label="Next Due" value={pm.nextDue} />
        <Field label="Assigned Technician" value={pm.assignedTechnician} />
        <Field label="Estimated Duration" value={`${pm.estimatedDurationHours} hrs`} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Frequency</div>
          <Badge variant={frequencyBadgeVariant(pm.frequency)}>{frequencyLabel(pm.frequency)}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
          <Badge variant={statusBadgeVariant(pm.status)}>{statusLabel(pm.status)}</Badge>
        </div>
      </Card>

      <Card title="Checklist">
        <ul style={{ margin: 0, paddingLeft: spacing.md, color: colors.text }}>
          {pm.checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Card>

      <Card title="Related Work Orders">
        {pm.relatedWorkOrders.length === 0 ? (
          <div style={{ color: colors.textMuted }}>No related work orders.</div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
            {pm.relatedWorkOrders.map((workOrderId) => (
              <Badge key={workOrderId} variant="info">
                {workOrderId}
              </Badge>
            ))}
          </div>
        )}
      </Card>

      <Timeline
        title="PM Schedule Timeline"
        activities={pm.timeline.map((entry) => `${entry.date} — ${entry.event}`)}
      />
    </div>
  );
}
