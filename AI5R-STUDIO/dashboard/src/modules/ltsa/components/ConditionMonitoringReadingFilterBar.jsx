import { SearchBox } from "../../../design-system";

/**
 * UI-D3.2 -- Condition Monitoring Reading filter bar
 *
 * Filter criteria:
 * - Search / Asset: filters by reading ID or equipment tag
 * - Workflow Status: filters by real workflow_status (DRAFT, SUBMITTED, RETURNED_FOR_CORRECTION, FINALIZED)
 * - Leak Status: filters by real leak booleans (All, Leak Detected, No Leak)
 * - Area: filters by resolved area from loaded data
 * - Clear: resets active filters
 */

const WORKFLOW_STATUS_OPTIONS = [
  { value: "ALL", label: "All Workflow Status" },
  { value: "DRAFT", label: "Draft" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "RETURNED_FOR_CORRECTION", label: "Returned for Correction" },
  { value: "FINALIZED", label: "Finalized" },
];

export default function ConditionMonitoringReadingFilterBar({
  searchValue,
  onSearchChange,
  statusFilter = "ALL",
  onStatusFilterChange,
  leakFilter,
  onLeakFilterChange,
  areaFilter = "ALL",
  onAreaFilterChange,
  areaOptions = [],
  onClear,
}) {
  const isFiltered =
    searchValue.trim() !== "" ||
    (statusFilter && statusFilter !== "ALL") ||
    leakFilter !== "ALL" ||
    areaFilter !== "ALL";

  return (
    <div className="cmon-filter-bar">
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by reading ID or equipment tag..."
      />

      {onStatusFilterChange && (
        <select
          aria-label="Filter by status"
          className="cmon-filter-select"
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value)}
        >
          {WORKFLOW_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      <select
        aria-label="Leak status"
        className="cmon-filter-select"
        value={leakFilter}
        onChange={(event) => onLeakFilterChange(event.target.value)}
      >
        <option value="ALL">All Seal Leak Status</option>
        <option value="LEAK">Leak Detected</option>
        <option value="NORMAL">No Leak</option>
        <option value="PARTIAL">Partially Recorded</option>
        <option value="UNKNOWN">Not Recorded</option>
      </select>

      {onAreaFilterChange && (
        <select
          aria-label="Filter by area"
          className="cmon-filter-select"
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
        <button type="button" className="cmon-filter-clear" onClick={onClear} disabled={!isFiltered}>
          Clear
        </button>
      )}
    </div>
  );
}
