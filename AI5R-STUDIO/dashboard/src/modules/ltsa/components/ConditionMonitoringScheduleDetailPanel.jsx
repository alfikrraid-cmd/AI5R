import { Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function ConditionMonitoringScheduleDetailPanel({ schedule, onViewAsset360, canDelete = false, onDelete }) {
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
      <h2 style={{ marginTop: 0 }}>{schedule.id}</h2>

      <Card title="Schedule Summary">
        <Field
          label="Equipment"
          value={schedule.area ? `${schedule.equipmentTag} — ${schedule.area}` : schedule.equipmentTag}
        />
        <Field label="Frequency" value={schedule.frequency ?? "Not recorded"} />
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
        {canDelete && <Button onClick={() => { const reason = window.prompt(`Deactivate ${schedule.id}:`); if (reason?.trim() && window.confirm(`Deactivate ${schedule.id}?`)) onDelete?.(schedule.id, reason.trim()); }}>Deactivate Schedule</Button>}
      </Card>
    </div>
  );
}
