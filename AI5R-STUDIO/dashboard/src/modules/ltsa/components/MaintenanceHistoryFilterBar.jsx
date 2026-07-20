import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { eventTypeLabel, filterStatusLabel } from "../utils/maintenanceHistory";

const EVENT_TYPES = ["PM", "CM", "WO"];

const selectStyle = {
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
};

const fieldStyle = { display: "flex", flexDirection: "column", gap: spacing.xs };
const labelStyle = { color: colors.textMuted, fontSize: 12 };

export default function MaintenanceHistoryFilterBar({
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
  eventTypeFilter,
  onEventTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  statusOptions,
  technicianFilter,
  onTechnicianFilterChange,
  technicianOptions,
}) {
  return (
    <div style={{ display: "flex", gap: spacing.md, flexWrap: "wrap", marginBottom: spacing.md }}>
      <div style={fieldStyle}>
        <label htmlFor="mh-date-from" style={labelStyle}>
          Date From
        </label>
        <input
          id="mh-date-from"
          type="date"
          value={dateFrom}
          onChange={(event) => onDateFromChange(event.target.value)}
          style={selectStyle}
        />
      </div>

      <div style={fieldStyle}>
        <label htmlFor="mh-date-to" style={labelStyle}>
          Date To
        </label>
        <input
          id="mh-date-to"
          type="date"
          value={dateTo}
          onChange={(event) => onDateToChange(event.target.value)}
          style={selectStyle}
        />
      </div>

      <div style={fieldStyle}>
        <label htmlFor="mh-event-type" style={labelStyle}>
          Event Type
        </label>
        <select
          id="mh-event-type"
          value={eventTypeFilter}
          onChange={(event) => onEventTypeFilterChange(event.target.value)}
          style={selectStyle}
        >
          <option value="ALL">All Types</option>
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {eventTypeLabel(type)}
            </option>
          ))}
        </select>
      </div>

      <div style={fieldStyle}>
        <label htmlFor="mh-status" style={labelStyle}>
          Status
        </label>
        <select
          id="mh-status"
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value)}
          style={selectStyle}
        >
          <option value="ALL">All Statuses</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {filterStatusLabel(status)}
            </option>
          ))}
        </select>
      </div>

      <div style={fieldStyle}>
        <label htmlFor="mh-technician" style={labelStyle}>
          Assigned Technician
        </label>
        <select
          id="mh-technician"
          value={technicianFilter}
          onChange={(event) => onTechnicianFilterChange(event.target.value)}
          style={selectStyle}
        >
          <option value="ALL">All Technicians</option>
          {technicianOptions.map((technician) => (
            <option key={technician} value={technician}>
              {technician}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
