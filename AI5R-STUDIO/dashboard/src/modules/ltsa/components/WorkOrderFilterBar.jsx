import { SearchBox } from "../../../design-system";
import { statusLabel } from "../utils/workOrderStatus";

/**
 * UI-D2A -- Work Order Workspace reference rebuild. Restyled light
 * (`.ltsa-open-design` token scope) and extended with Priority/Area/Clear
 * controls per Chief's approved reference -- Priority and Area are both
 * already-real fields on every mapped work order (workOrderMapping.js),
 * simply never exposed as filters before. New props are optional with
 * safe no-op defaults so every existing caller/test that doesn't pass
 * them keeps working unchanged (search + status alone).
 */
export default function WorkOrderFilterBar({
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
  priorityFilter = "ALL",
  onPriorityFilterChange,
  priorityOptions = [],
  areaFilter = "ALL",
  onAreaFilterChange,
  areaOptions = [],
  onClear,
}) {
  const isFiltered =
    searchValue.trim() !== "" || statusFilter !== "ALL" || priorityFilter !== "ALL" || areaFilter !== "ALL";

  return (
    <div className="workorder-filter-bar">
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by ID, title, or equipment tag..."
      />

      <select
        aria-label="Filter by status"
        className="workorder-filter-select"
        value={statusFilter}
        onChange={(event) => onStatusFilterChange(event.target.value)}
      >
        <option value="ALL">All Statuses</option>
        {statusOptions.map((status) => (
          <option key={status} value={status}>
            {statusLabel(status)}
          </option>
        ))}
      </select>

      {onPriorityFilterChange && (
        <select
          aria-label="Filter by priority"
          className="workorder-filter-select"
          value={priorityFilter}
          onChange={(event) => onPriorityFilterChange(event.target.value)}
        >
          <option value="ALL">All Priorities</option>
          {priorityOptions.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
      )}

      {onAreaFilterChange && (
        <select
          aria-label="Filter by area"
          className="workorder-filter-select"
          value={areaFilter}
          onChange={(event) => onAreaFilterChange(event.target.value)}
        >
          <option value="ALL">All Areas</option>
          {areaOptions.map((area) => (
            <option key={area} value={area}>
              {area}
            </option>
          ))}
        </select>
      )}

      {onClear && (
        <button
          type="button"
          className="workorder-filter-clear"
          onClick={onClear}
          disabled={!isFiltered}
        >
          Clear
        </button>
      )}
    </div>
  );
}
