import { SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

export default function PumpFilterBar({
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
        placeholder="Search by tag, name, or manufacturer..."
      />

      <select
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
        <option value="ALL">All Statuses</option>

        {statusOptions.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
    </div>
  );
}
