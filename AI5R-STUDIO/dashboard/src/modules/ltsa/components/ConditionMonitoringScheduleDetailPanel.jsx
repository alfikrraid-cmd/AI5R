import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { cmonScheduleStatusBadgeVariant, cmonScheduleStatusLabel } from "../utils/cmonScheduleStatus";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function ConditionMonitoringScheduleDetailPanel({
  schedule,
  onViewAsset360,
  canDelete = false,
  onDelete,
  canEdit = false,
  onEdit,
}) {
  if (!schedule) {
    return (
      <EmptyState
        title="No Condition Monitoring schedule selected"
        description="Select a schedule from the list to view its details."
      />
    );
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm }}>
        <h2 style={{ margin: 0 }}>{schedule.id}</h2>
        {/* MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- migration 029's
            PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED lifecycle, same
            computed-display convention PMOpenDesignView.jsx's own
            STATUS_META badge already uses for PM. */}
        <Badge variant={cmonScheduleStatusBadgeVariant(schedule.status)}>{cmonScheduleStatusLabel(schedule.status)}</Badge>
      </div>

      <Card title="Schedule Summary">
        <Field
          label="Equipment"
          value={schedule.area ? `${schedule.equipmentTag} — ${schedule.area}` : schedule.equipmentTag}
        />
        <Field label="Frequency" value={schedule.frequency ?? "Not recorded"} />
        <Field label="Next Due" value={schedule.nextDue ?? "Not set"} />
      </Card>

      <Card title="Applicable Parameters">
        {schedule.applicableParameters.length === 0 ? (
          <div style={{ color: colors.textMuted }}>No applicable parameters recorded.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: spacing.md, color: colors.text }}>
            {schedule.applicableParameters.map((parameter) => (
              <li key={parameter}>{parameter}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Quick Actions">
        <Button onClick={() => onViewAsset360?.(schedule.equipmentTag)}>View Asset 360</Button>
        {/* MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- same MAINTENANCE_WRITE
            gate the backend PATCH endpoint itself requires. */}
        {canEdit && <Button onClick={() => onEdit?.(schedule)}>Edit Schedule</Button>}
        {canDelete && <Button onClick={() => { const reason = window.prompt(`Deactivate ${schedule.id}:`); if (reason?.trim() && window.confirm(`Deactivate ${schedule.id}?`)) onDelete?.(schedule.id, reason.trim()); }}>Deactivate Schedule</Button>}
      </Card>
    </div>
  );
}
