import { Badge, Card, EmptyState, Timeline } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { priorityBadgeVariant, statusBadgeVariant, statusLabel } from "../utils/workOrderStatus";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function WorkOrderDetailPanel({ workOrder }) {
  if (!workOrder) {
    return (
      <EmptyState
        title="No work order selected"
        description="Select a work order from the registry table to view its details."
      />
    );
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{workOrder.title}</h2>

      <Card title="Work Order Summary">
        <Field label="Work Order ID" value={workOrder.id} />
        <Field label="Equipment Tag" value={workOrder.equipmentTag} />
        <Field label="Area" value={workOrder.area} />
        <Field label="Work Type" value={workOrder.workType} />
        <Field label="Assigned Technician" value={workOrder.assignedTechnician} />
        <Field label="Requested By" value={workOrder.requestedBy} />
        <Field label="Created Date" value={workOrder.createdDate} />
        <Field label="Due Date" value={workOrder.dueDate} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Priority</div>
          <Badge variant={priorityBadgeVariant(workOrder.priority)}>{workOrder.priority}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
          <Badge variant={statusBadgeVariant(workOrder.status)}>{statusLabel(workOrder.status)}</Badge>
        </div>
      </Card>

      <Card title="Description">
        <Field label="Description" value={workOrder.description} />
      </Card>

      <Timeline
        title="Work Order Timeline"
        activities={workOrder.timeline.map((entry) => `${entry.date} — ${entry.event}`)}
      />
    </div>
  );
}
