import { SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

export default function ConditionMonitoringReadingFilterBar({
  searchValue,
  onSearchChange,
  leakFilter,
  onLeakFilterChange,
}) {
  return (
    <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap", marginBottom: spacing.md }}>
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by reading ID or equipment tag..."
      />

      <select
        aria-label="Filter by leak status"
        value={leakFilter}
        onChange={(event) => onLeakFilterChange(event.target.value)}
        style={{
          background: colors.panel,
          color: colors.text,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.xs,
          padding: `${spacing.xs}px ${spacing.sm}px`,
        }}
      >
        <option value="ALL">All Readings</option>
        <option value="LEAK">Leak Detected</option>
        <option value="NORMAL">Normal</option>
      </select>
    </div>
  );
}
