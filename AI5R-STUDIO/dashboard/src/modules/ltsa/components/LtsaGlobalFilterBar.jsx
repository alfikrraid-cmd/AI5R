import { useMemo } from "react";
import colors from "../../../design-system/theme/colors";

export const ALL_AREAS = "ALL";

/**
 * LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- the Executive Dashboard's ONE
 * global filter bar, fully controlled by ExecutiveDashboard.
 *
 * - Area: "All Areas" plus exactly the backend's `authorizedAreas`
 *   ({code, label}, derived server-side from resolve_area_scope) -- never a
 *   hard-coded or data-derived list. Selecting an area changes the whole
 *   dashboard (onAreaChange); the backend re-checks it on every request.
 * - Pump / dates: narrow the analytics requests only (onFilterChange sends
 *   pump_tag/start_date/end_date; area is never sent from here).
 */
export default function LtsaGlobalFilterBar({
  area = ALL_AREAS,
  authorizedAreas = [],
  onAreaChange,
  filterOptions = {},
  filters = {},
  onFilterChange,
}) {
  const pumps = filterOptions.pumps || [];
  const dateRange = filterOptions.date_range || {};
  const selectedPump = filters.pump_tag || "";
  const startDate = filters.start_date ?? dateRange.min_date ?? "";
  const endDate = filters.end_date ?? dateRange.max_date ?? "";

  // Pumps of the selected area, matched on the canonical area so alias-coded
  // pumps (SPK, OIL MOVEMENT, UTILITIES) stay under their area.
  const availablePumps = useMemo(() => {
    if (area === ALL_AREAS) return pumps;
    return pumps.filter((p) => (p.canonical_area ?? p.area) === area);
  }, [pumps, area]);

  function emit(next) {
    onFilterChange?.({
      pump_tag: selectedPump || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      ...next,
    });
  }

  const handleReset = () => {
    onAreaChange?.(ALL_AREAS);
    onFilterChange?.({
      pump_tag: undefined,
      start_date: dateRange.min_date || undefined,
      end_date: dateRange.max_date || undefined,
    });
  };

  const selectStyle = {
    background: colors.background,
    color: colors.text,
    border: `1px solid ${colors.border}`,
    borderRadius: "6px",
    padding: "6px 12px",
    fontSize: "0.8rem",
    outline: "none",
  };

  const selectedAreaLabel =
    area === ALL_AREAS ? "All Areas" : authorizedAreas.find((a) => a.code === area)?.label ?? area;
  const hasActiveFilters = Boolean(area !== ALL_AREAS || selectedPump);

  return (
    <div
      style={{
        background: colors.panel,
        border: `1px solid ${colors.border}`,
        borderRadius: "8px",
        padding: "12px 16px",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
        marginBottom: "16px",
      }}
      data-testid="ltsa-global-filter-bar"
    >
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "12px" }}>
        <span style={{ fontSize: "0.8rem", fontWeight: 600, color: colors.textMuted, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Scope & Filter:
        </span>

        {/* Global Area Filter -- authorized areas only */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="filter-area" style={{ fontSize: "0.75rem", color: colors.textMuted }}>
            Area:
          </label>
          <select
            id="filter-area"
            value={area}
            onChange={(e) => onAreaChange?.(e.target.value)}
            style={{ ...selectStyle, fontWeight: 600 }}
            aria-label="Filter by Area"
          >
            <option value={ALL_AREAS}>All Areas</option>
            {authorizedAreas.map((a) => (
              <option key={a.code} value={a.code}>
                {a.label}
              </option>
            ))}
          </select>
        </div>

        {/* Pump Tag Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="filter-pump" style={{ fontSize: "0.75rem", color: colors.textMuted }}>
            Pump:
          </label>
          <select
            id="filter-pump"
            value={selectedPump}
            onChange={(e) => emit({ pump_tag: e.target.value || undefined })}
            style={{ ...selectStyle, maxWidth: "160px" }}
            aria-label="Filter by Pump"
          >
            <option value="">All Pumps</option>
            {availablePumps.map((p) => (
              <option key={p.tag_number} value={p.tag_number}>
                {p.tag_number} ({p.pump_type || "Pump"})
              </option>
            ))}
          </select>
        </div>

        {/* Date Range Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="filter-start-date" style={{ fontSize: "0.75rem", color: colors.textMuted }}>
            From:
          </label>
          <input
            id="filter-start-date"
            type="date"
            value={startDate}
            onChange={(e) => emit({ start_date: e.target.value || undefined })}
            style={selectStyle}
            aria-label="Filter Start Date"
          />
          <label htmlFor="filter-end-date" style={{ fontSize: "0.75rem", color: colors.textMuted }}>
            To:
          </label>
          <input
            id="filter-end-date"
            type="date"
            value={endDate}
            onChange={(e) => emit({ end_date: e.target.value || undefined })}
            style={selectStyle}
            aria-label="Filter End Date"
          />
        </div>
      </div>

      {/* Selected scope & Reset */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span
          data-testid="selected-area-badge"
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: hasActiveFilters ? colors.info : colors.textMuted,
            border: `1px solid ${hasActiveFilters ? colors.info : colors.border}`,
            borderRadius: "999px",
            padding: "2px 10px",
          }}
        >
          {selectedAreaLabel}
        </span>
        <button
          type="button"
          onClick={handleReset}
          style={{
            background: "transparent",
            border: `1px solid ${colors.border}`,
            color: colors.textMuted,
            borderRadius: "6px",
            padding: "5px 12px",
            fontSize: "0.75rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = colors.text;
            e.currentTarget.style.borderColor = colors.info;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = colors.textMuted;
            e.currentTarget.style.borderColor = colors.border;
          }}
        >
          Reset Filters
        </button>
      </div>
    </div>
  );
}
