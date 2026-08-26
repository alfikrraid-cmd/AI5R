import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { cmonScheduleStatusBadgeVariant, cmonScheduleStatusLabel } from "../utils/cmonScheduleStatus";

const HEADERS = ["Schedule ID", "Equipment", "Frequency", "Next Due", "Status", "Applicable Parameters"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- migration 029 adds status/
// next_due (ADR-CONDITION-MONITORING-001's own Open Question 1, resolved
// by the owner-approved PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED
// lifecycle, mirroring pm_schedule's identical shape).
export default function ConditionMonitoringScheduleTable({ schedules, selectedId, onSelect }) {
  if (schedules.length === 0) {
    return (
      <EmptyState
        title="No Condition Monitoring schedules match"
        description="Adjust the search text to see registry results."
      />
    );
  }

  function handleKeyDown(event, id) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {HEADERS.map((header) => (
              <th key={header} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {schedules.map((schedule) => {
            const isSelected = schedule.id === selectedId;

            return (
              <tr
                key={schedule.id}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(schedule.id)}
                onKeyDown={(event) => handleKeyDown(event, schedule.id)}
                style={{
                  cursor: "pointer",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{schedule.id}</div>
                </td>
                <td style={tdStyle}>
                  <div>{schedule.equipmentTag}</div>
                  {schedule.area ? (
                    <div style={{ color: colors.textMuted, fontSize: 12 }}>{schedule.area}</div>
                  ) : null}
                </td>
                <td style={tdStyle}>{schedule.frequency ?? "—"}</td>
                <td style={tdStyle}>{schedule.nextDue ?? "—"}</td>
                <td style={tdStyle}>
                  <Badge variant={cmonScheduleStatusBadgeVariant(schedule.status)}>{cmonScheduleStatusLabel(schedule.status)}</Badge>
                </td>
                <td style={tdStyle}>{schedule.applicableParameters.length}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
