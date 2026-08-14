import { SearchBox } from "../../../design-system";

function Filter({ label, value, options, onChange }) {
  return (
    <label className="equipment-filter">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="ALL">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function EquipmentFilterBar({
  search,
  onSearchChange,
  filters,
  onFilterChange,
  options,
}) {
  return (
    <div className="equipment-toolbar" aria-label="Equipment toolbar">
      <SearchBox
        value={search}
        onChange={onSearchChange}
        placeholder="Search equipment, tag, manufacturer, or model"
      />

      <Filter
        label="Area"
        value={filters.area}
        options={options.areas}
        onChange={(value) => onFilterChange("area", value)}
      />
      <Filter
        label="Equipment Type"
        value={filters.equipmentType}
        options={options.equipmentTypes}
        onChange={(value) => onFilterChange("equipmentType", value)}
      />
      <Filter
        label="Status"
        value={filters.status}
        options={options.statuses}
        onChange={(value) => onFilterChange("status", value)}
      />
    </div>
  );
}
