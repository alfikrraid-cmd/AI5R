import { SearchBox } from "../../../design-system";
import { statusLabel } from "../utils/pmStatus";

/**
 * UI-D2B -- Preventive Maintenance reference rebuild. Restyled light
 * (`.ltsa-open-design` token scope, PM-specific `.pm-filter-*` classes in
 * PM.css) and extended with an Area/Clear control, same pattern
 * UI-D2A.1 established for Work Order. Area is already a real field on
 * every mapped PM schedule (pmMapping.js's withResolvedArea), simply
 * never exposed as a filter before. New props are optional with safe
 * no-op defaults so every existing caller/test that doesn't pass them
 * keeps working unchanged (search + status alone).
 */
export default function PMFilterBar({
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
  areaFilter = "ALL",
  onAreaFilterChange,
  areaOptions = [],
  onClear,
}) {
  const isFiltered = searchValue.trim() !== "" || statusFilter !== "ALL" || areaFilter !== "ALL";

  return (
    <div className="pm-filter-bar">
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by PM ID, procedure, or equipment tag..."
      />

      <select
        aria-label="Filter by status"
        className="pm-filter-select"
        value={statusFilter}
        onChange={(event) => onStatusFilterChange(event.target.value)}
      >
        {/* MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "ALL" is the default
            active work queue (every status except Completed/Cancelled),
            not literally every row; Completed/Cancelled stay reachable by
            selecting them explicitly from statusOptions below. */}
        <option value="ALL">Active Queue (excludes Completed / Cancelled)</option>

        {statusOptions.map((status) => (
          <option key={status} value={status}>
            {statusLabel(status)}
          </option>
        ))}
      </select>

      {onAreaFilterChange && (
        <select
          aria-label="Filter by area"
          className="pm-filter-select"
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
        <button type="button" className="pm-filter-clear" onClick={onClear} disabled={!isFiltered}>
          Clear
        </button>
      )}
    </div>
  );
}
