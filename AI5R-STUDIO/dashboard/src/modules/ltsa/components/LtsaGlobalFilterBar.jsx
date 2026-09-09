import { useEffect, useMemo, useState } from "react";
import colors from "../../../design-system/theme/colors";
import { getLtsaAnalyticsFilters } from "../../../api/ai5rClient";

export default function LtsaGlobalFilterBar({
  filters = {},
  onFilterChange,
}) {
  const [filterOptions, setFilterOptions] = useState({ areas: [], pumps: [], date_range: {} });
  const [selectedArea, setSelectedArea] = useState(filters.area || "");
  const [selectedPump, setSelectedPump] = useState(filters.pump_tag || "");
  const [startDate, setStartDate] = useState(filters.start_date || "");
  const [endDate, setEndDate] = useState(filters.end_date || "");

  useEffect(() => {
    let active = true;
    getLtsaAnalyticsFilters()
      .then((data) => {
        if (active && data) {
          setFilterOptions(data);
          if (!startDate && data.date_range?.min_date) {
            setStartDate(data.date_range.min_date);
          }
          if (!endDate && data.date_range?.max_date) {
            setEndDate(data.date_range.max_date);
          }
        }
      })
      .catch(() => {
        // absorb filter failure gracefully
      });
    return () => {
      active = false;
    };
  }, []);

  // Filter pumps available in the selected area
  const availablePumps = useMemo(() => {
    if (!filterOptions.pumps) return [];
    if (!selectedArea) return filterOptions.pumps;
    return filterOptions.pumps.filter((p) => p.area === selectedArea);
  }, [filterOptions.pumps, selectedArea]);

  const handleAreaChange = (e) => {
    const area = e.target.value;
    setSelectedArea(area);
    setSelectedPump(""); // Reset pump selection when area changes
    onFilterChange?.({
      area: area || undefined,
      contract_area: area || undefined,
      pump_tag: undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  const handlePumpChange = (e) => {
    const pump = e.target.value;
    setSelectedPump(pump);
    onFilterChange?.({
      area: selectedArea || undefined,
      contract_area: selectedArea || undefined,
      pump_tag: pump || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  const handleStartDateChange = (e) => {
    const date = e.target.value;
    setStartDate(date);
    onFilterChange?.({
      area: selectedArea || undefined,
      contract_area: selectedArea || undefined,
      pump_tag: selectedPump || undefined,
      start_date: date || undefined,
      end_date: endDate || undefined,
    });
  };

  const handleEndDateChange = (e) => {
    const date = e.target.value;
    setEndDate(date);
    onFilterChange?.({
      area: selectedArea || undefined,
      contract_area: selectedArea || undefined,
      pump_tag: selectedPump || undefined,
      start_date: startDate || undefined,
      end_date: date || undefined,
    });
  };

  const handleReset = () => {
    setSelectedArea("");
    setSelectedPump("");
    const minD = filterOptions.date_range?.min_date || "2026-07-01";
    const maxD = filterOptions.date_range?.max_date || "2026-07-31";
    setStartDate(minD);
    setEndDate(maxD);
    onFilterChange?.({
      area: undefined,
      contract_area: undefined,
      pump_tag: undefined,
      start_date: minD,
      end_date: maxD,
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

  const hasActiveFilters = Boolean(selectedArea || selectedPump);

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

        {/* Contract Area / Area Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="filter-area" style={{ fontSize: "0.75rem", color: colors.textMuted }}>
            Area:
          </label>
          <select
            id="filter-area"
            value={selectedArea}
            onChange={handleAreaChange}
            style={selectStyle}
            aria-label="Filter by Area"
          >
            <option value="">All Areas (Fleet)</option>
            {filterOptions.areas.map((a) => (
              <option key={a.area} value={a.area}>
                {a.area} ({a.pump_count} pumps)
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
            onChange={handlePumpChange}
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
            onChange={handleStartDateChange}
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
            onChange={handleEndDateChange}
            style={selectStyle}
            aria-label="Filter End Date"
          />
        </div>
      </div>

      {/* Reset & Status */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {hasActiveFilters && (
          <span style={{ fontSize: "0.75rem", color: colors.info }}>
            Filtered View
          </span>
        )}
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

