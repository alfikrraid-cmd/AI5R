import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { statusBadgeVariant as pmScheduleStatusBadgeVariant, statusLabel as pmScheduleStatusLabel } from "../utils/pmStatus";

/**
 * The "what SHOULD happen to this asset going forward" zone
 * (DISCOVERY-ASSET360-UI-001 / ADR-ASSET360-001) -- deliberately separate
 * from the History timeline below it, since a Plan is not a past event.
 * pmSchedules are already mapped via pmMapping.mapPMScheduleRecord (same
 * shape PM.jsx itself uses). conditionMonitoringSchedules are raw API
 * records -- no dedicated mapping file exists for this panel's own use
 * (APP-CMON-001's own workspace has its own, in
 * utils/conditionMonitoringMapping.js; reusing it here isn't needed for
 * the two fields this panel displays).
 *
 * Condition Monitoring Schedule rows navigate to the Condition Monitoring
 * workspace (APP-CMON-001's "Navigation from Asset 360 Active Plans"
 * requirement) via `onNavigate("cmon", { selectId })`. PM Schedule rows
 * are deliberately left as before -- promoting them wasn't part of this
 * MWO's scope.
 */
export default function ActivePlansPanel({ pmSchedules, conditionMonitoringSchedules, onNavigate }) {
  const hasAny = pmSchedules.length > 0 || conditionMonitoringSchedules.length > 0;

  if (!hasAny) {
    return (
      <Card title="Active Plans">
        <EmptyState
          title="No active plans"
          description="No PM Schedule or Condition Monitoring Schedule exists for this asset."
        />
      </Card>
    );
  }

  function handleKeyDown(event, code) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onNavigate?.("cmon", { selectId: code });
    }
  }

  return (
    <Card title="Active Plans">
      {pmSchedules.map((pm) => (
        <div
          key={pm.id}
          style={{ marginBottom: spacing.sm, paddingBottom: spacing.sm, borderBottom: `1px solid ${colors.border}` }}
        >
          <div style={{ fontWeight: "bold", color: colors.text }}>{pm.procedure}</div>
          <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: spacing.xs }}>
            PM Schedule — {pm.frequency ?? "—"} — Next due: {pm.nextDue ?? "—"}
          </div>
          <Badge variant={pmScheduleStatusBadgeVariant(pm.status)}>{pmScheduleStatusLabel(pm.status)}</Badge>
        </div>
      ))}

      {conditionMonitoringSchedules.map((schedule) => {
        const code = schedule.condition_monitoring_schedule_code;
        const clickable = Boolean(onNavigate);

        return (
          <div
            key={code}
            role={clickable ? "button" : undefined}
            tabIndex={clickable ? 0 : undefined}
            onClick={clickable ? () => onNavigate("cmon", { selectId: code }) : undefined}
            onKeyDown={clickable ? (event) => handleKeyDown(event, code) : undefined}
            style={{ marginBottom: spacing.sm, cursor: clickable ? "pointer" : "default" }}
          >
            <div style={{ fontWeight: "bold", color: colors.text }}>{code}</div>
            <div style={{ fontSize: 12, color: colors.textMuted }}>
              Condition Monitoring — {schedule.frequency ?? "—"}
            </div>
          </div>
        );
      })}
    </Card>
  );
}
