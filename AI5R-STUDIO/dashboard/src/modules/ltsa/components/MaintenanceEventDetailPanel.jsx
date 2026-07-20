import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  eventStatusBadgeVariant,
  eventStatusLabel,
  eventTypeBadgeVariant,
  eventTypeLabel,
} from "../utils/maintenanceHistory";
import { frequencyLabel, triggerTypeLabel } from "../utils/pmStatus";
import { failureCategoryLabel, priorityBadgeVariant, severityBadgeVariant } from "../utils/cmStatus";
import { priorityBadgeVariant as woPriorityBadgeVariant } from "../utils/workOrderStatus";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

function PMDetails({ pm }) {
  return (
    <Card title="Preventive Maintenance Details">
      <Field label="Frequency" value={frequencyLabel(pm.frequency)} />
      <Field label="Trigger Type" value={triggerTypeLabel(pm.triggerType)} />
      <Field label="Estimated Duration" value={`${pm.estimatedDurationHours} hrs`} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>Checklist</div>
        <ul style={{ margin: 0, paddingLeft: spacing.md, color: colors.text }}>
          {pm.checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

function CMDetails({ cm }) {
  return (
    <Card title="Corrective Maintenance Details">
      <Field label="Failure Category" value={failureCategoryLabel(cm.failureCategory)} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Severity</div>
        <Badge variant={severityBadgeVariant(cm.severity)}>{cm.severity}</Badge>
      </div>

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Priority</div>
        <Badge variant={priorityBadgeVariant(cm.priority)}>{cm.priority}</Badge>
      </div>

      <Field label="Root Cause" value={cm.rootCause} />
      <Field label="Immediate Action" value={cm.immediateAction} />
      <Field label="Corrective Action" value={cm.correctiveAction} />
      <Field label="Downtime" value={`${cm.downtimeHours} hrs`} />
    </Card>
  );
}

function WODetails({ wo }) {
  return (
    <Card title="Work Order Details">
      <Field label="Work Type" value={wo.workType} />
      <Field label="Requested By" value={wo.requestedBy} />
      <Field label="Due Date" value={wo.dueDate} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Priority</div>
        <Badge variant={woPriorityBadgeVariant(wo.priority)}>{wo.priority}</Badge>
      </div>

      <Field label="Description" value={wo.description} />
    </Card>
  );
}

export default function MaintenanceEventDetailPanel({ event }) {
  if (!event) {
    return (
      <EmptyState
        title="No event selected"
        description="Select an event from the timeline to view its details."
      />
    );
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{event.title}</h2>

      <Card title="Event Summary">
        <Field label="Event ID" value={event.id} />
        <Field label="Date" value={event.date ?? "—"} />
        <Field label="Assigned Technician" value={event.assignedTechnician} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Type</div>
          <Badge variant={eventTypeBadgeVariant(event.type)}>{eventTypeLabel(event.type)}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
          <Badge variant={eventStatusBadgeVariant(event)}>{eventStatusLabel(event)}</Badge>
        </div>
      </Card>

      {event.type === "PM" ? <PMDetails pm={event.raw} /> : null}
      {event.type === "CM" ? <CMDetails cm={event.raw} /> : null}
      {event.type === "WO" ? <WODetails wo={event.raw} /> : null}
    </div>
  );
}
