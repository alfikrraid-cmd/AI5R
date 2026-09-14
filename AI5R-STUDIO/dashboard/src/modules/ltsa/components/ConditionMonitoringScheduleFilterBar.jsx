import { SearchBox } from "../../../design-system";
import { cmonScheduleStatusLabel } from "../utils/cmonScheduleStatus";

// UI-D2C -- restyled light (`.ltsa-open-design` token scope,
// `.cmon-filter-*` classes, shared with the Readings filter bar's own
// classes in ConditionMonitoring.css), same visual pass UI-D2A.1/UI-D2B
// already gave Work Order/PM. Behavior unchanged: "ALL" is the default
// active work queue (every status except Completed/Cancelled), not
// literally every row -- Completed/Cancelled stay reachable by selecting
// them explicitly from statusOptions below.
export default function ConditionMonitoringScheduleFilterBar({
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
}) {
  return (
    <div className="cmon-filter-bar">
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by schedule ID or equipment tag..."
      />

      <select
        aria-label="Filter by status"
        className="cmon-filter-select"
        value={statusFilter}
        onChange={(event) => onStatusFilterChange(event.target.value)}
      >
        <option value="ALL">Active Queue (excludes Completed / Cancelled)</option>

        {statusOptions.filter(Boolean).map((status) => (
          <option key={status} value={status}>
            {cmonScheduleStatusLabel(status)}
          </option>
        ))}
      </select>
    </div>
  );
}
