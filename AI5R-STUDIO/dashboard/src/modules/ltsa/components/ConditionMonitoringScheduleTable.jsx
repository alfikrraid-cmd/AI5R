import { Badge, EmptyState } from "../../../design-system";
import { cmonScheduleStatusBadgeVariant, cmonScheduleStatusLabel } from "../utils/cmonScheduleStatus";

const HEADERS = ["Schedule ID", "Equipment", "Frequency", "Next Due", "Status", "Applicable Parameters"];

// UI-D2C -- restyled from the old dark inline-style table (colors.js/
// spacing.js) to the light `.ltsa-open-design` token scope
// (`.cmon-schedule-*` classes, ConditionMonitoring.css), mirroring the
// same visual pass UI-D2A.1/UI-D2B already gave the Work Order/PM
// registries. Columns, data, selection, and keyboard behavior are
// unchanged -- Schedules is the supporting (not condition-centric
// primary) view per this mission's own framing, so it gets a visual
// parity pass only, not the full mobile card-list/collapsed-summary/
// AssetIdentityHeader treatment the Readings view receives.
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
    <div className="cmon-schedule-table-wrap">
      <table className="cmon-schedule-table">
        <thead>
          <tr>
            {HEADERS.map((header) => (
              <th key={header}>{header}</th>
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
              >
                <td>
                  <div className="cmon-id">{schedule.id}</div>
                </td>
                <td>
                  <div>{schedule.equipmentTag}</div>
                  {schedule.area ? <div className="cmon-subtext">{schedule.area}</div> : null}
                </td>
                <td>{schedule.frequency ?? "—"}</td>
                <td>{schedule.nextDue ?? "—"}</td>
                <td>
                  <Badge variant={cmonScheduleStatusBadgeVariant(schedule.status)}>{cmonScheduleStatusLabel(schedule.status)}</Badge>
                </td>
                <td>{schedule.applicableParameters.length}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
