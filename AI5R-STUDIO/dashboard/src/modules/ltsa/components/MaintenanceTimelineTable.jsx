import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  eventStatusBadgeVariant,
  eventStatusLabel,
  eventTypeBadgeVariant,
  eventTypeLabel,
} from "../utils/maintenanceHistory";

const HEADERS = ["Date", "Type", "Event", "Status", "Assigned Technician"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function MaintenanceTimelineTable({ events, selectedId, onSelect }) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No history matches"
        description="Adjust the filters to see events in this asset's timeline."
      />
    );
  }

  function handleKeyDown(event, id) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {HEADERS.map((header) => (
              <th key={header} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {events.map((event) => {
            const isSelected = event.id === selectedId;

            return (
              <tr
                key={event.id}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(event.id)}
                onKeyDown={(keyEvent) => handleKeyDown(keyEvent, event.id)}
                style={{
                  cursor: "pointer",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                <td style={tdStyle}>{event.date ?? "—"}</td>
                <td style={tdStyle}>
                  <Badge variant={eventTypeBadgeVariant(event.type)}>{eventTypeLabel(event.type)}</Badge>
                </td>
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{event.id}</div>
                  <div style={{ fontSize: 13 }}>{event.title}</div>
                </td>
                <td style={tdStyle}>
                  <Badge variant={eventStatusBadgeVariant(event)}>{eventStatusLabel(event)}</Badge>
                </td>
                <td style={tdStyle}>{event.assignedTechnician}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
