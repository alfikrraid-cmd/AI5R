import { SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

export default function SealFilterBar({
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
  stockFilter = "ALL",
  onStockFilterChange = () => {},
}) {
  const stockOptions = [
    { key: "ALL", label: "All Stock" },
    { key: "IN_STOCK", label: "In Stock (>0)" },
    { key: "OUT_OF_STOCK", label: "Out of Stock (0)" },
    { key: "UNKNOWN", label: "Unknown / N/A" },
  ];

  return (
    <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap", marginBottom: spacing.md, alignItems: "center" }}>
      <SearchBox
        value={searchValue}
        onChange={onSearchChange}
        placeholder="Search by code, type, size, pump tag, drawing, manufacturer..."
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
        <option value="ALL">All Statuses</option>

        {statusOptions.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>

      <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
        {stockOptions.map((opt) => {
          const isSelected = stockFilter === opt.key;
          return (
            <button
              key={opt.key}
              type="button"
              onClick={() => onStockFilterChange(opt.key)}
              style={{
                background: isSelected ? colors.primary : colors.panel,
                color: isSelected ? "#ffffff" : colors.textMuted,
                border: `1px solid ${isSelected ? colors.primary : colors.border}`,
                borderRadius: spacing.xs,
                padding: "4px 8px",
                fontSize: "12px",
                fontWeight: isSelected ? 600 : 400,
                cursor: "pointer",
              }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

