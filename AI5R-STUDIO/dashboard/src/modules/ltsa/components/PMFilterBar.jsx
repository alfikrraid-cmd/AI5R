import { SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { statusLabel } from "../utils/pmStatus";

export default function PMFilterBar({
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
        placeholder="Search by PM ID, procedure, or equipment tag..."
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
    </div>
  );
}
