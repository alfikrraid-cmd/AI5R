import { SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { cmonScheduleStatusLabel } from "../utils/cmonScheduleStatus";

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- status filter added,
// mirroring PMFilterBar.jsx's own convention exactly: "ALL" is the
// default active work queue (every status except Completed/Cancelled),
// not literally every row -- Completed/Cancelled stay reachable by
// selecting them explicitly from statusOptions below.
export default function ConditionMonitoringScheduleFilterBar({
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
}) {
  return (
    <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap", marginBottom: spacing.md }}>
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by schedule ID or equipment tag..."
      />

      <select
        aria-label="Filter by status"
        value={statusFilter}
        onChange={(event) => onStatusFilterChange(event.target.value)}
        style={{
          background: colors.panel,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          padding: `${spacing.xs}px ${spacing.sm}px`,
        }}
      >
        <option value="ALL">Active Queue (excludes Completed / Cancelled)</option>

        {statusOptions.map((status) => (
          <option key={status} value={status}>
            {cmonScheduleStatusLabel(status)}
          </option>
        ))}
      </select>
    </div>
  );
}
