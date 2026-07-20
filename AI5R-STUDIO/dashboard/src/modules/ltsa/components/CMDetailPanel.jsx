import { Badge, Card, EmptyState, Timeline } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  failureCategoryLabel,
  priorityBadgeVariant,
  severityBadgeVariant,
  statusBadgeVariant,
  statusLabel,
} from "../utils/cmStatus";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function CMDetailPanel({ cm }) {
  if (!cm) {
    return (
      <EmptyState
        title="No corrective maintenance report selected"
        description="Select a report from the list to view its details."
      />
    );
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{cm.failureDescription}</h2>

      <Card title="Corrective Maintenance Summary">
        <Field label="Equipment" value={cm.area ? `${cm.equipmentTag} — ${cm.area}` : cm.equipmentTag} />
        <Field label="Assigned Technician" value={cm.assignedTechnician} />
        <Field label="Downtime" value={`${cm.downtimeHours} hrs`} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Failure Category</div>
          <Badge variant="purple">{failureCategoryLabel(cm.failureCategory)}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Severity</div>
          <Badge variant={severityBadgeVariant(cm.severity)}>{cm.severity}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Priority</div>
          <Badge variant={priorityBadgeVariant(cm.priority)}>{cm.priority}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
          <Badge variant={statusBadgeVariant(cm.status)}>{statusLabel(cm.status)}</Badge>
        </div>
      </Card>

      <Card title="Root Cause & Actions">
        <Field label="Root Cause" value={cm.rootCause} />
        <Field label="Immediate Action" value={cm.immediateAction} />
        <Field label="Corrective Action" value={cm.correctiveAction} />
      </Card>

      <Card title="Related Records">
        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>Related Pump</div>
          {cm.relatedPump ? (
            <Badge variant="info">{cm.relatedPump}</Badge>
          ) : (
            <div style={{ color: colors.textMuted }}>No related pump.</div>
          )}
        </div>

        <div>
          <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
            Related Work Order
          </div>
          {cm.relatedWorkOrder ? (
            <Badge variant="info">{cm.relatedWorkOrder}</Badge>
          ) : (
            <div style={{ color: colors.textMuted }}>No related work order.</div>
          )}
        </div>
      </Card>

      <Timeline
        title="Corrective Maintenance Timeline"
        activities={cm.timeline.map((entry) => `${entry.date} — ${entry.event}`)}
      />
    </div>
  );
}
