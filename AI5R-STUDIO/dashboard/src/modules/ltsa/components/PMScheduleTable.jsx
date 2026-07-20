import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { frequencyBadgeVariant, frequencyLabel, statusBadgeVariant } from "../utils/pmStatus";

const HEADERS = ["PM ID", "Equipment", "Frequency", "Next Due", "Last Performed", "Assigned Technician", "Status"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function PMScheduleTable({ pmSchedules, selectedId, onSelect }) {
  if (pmSchedules.length === 0) {
    return (
      <EmptyState
        title="No PM schedules match"
        description="Adjust the search text or status filter to see registry results."
      />
    );
  }

  return (
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
        {pmSchedules.map((pm) => {
          const isSelected = pm.id === selectedId;

          return (
            <tr
              key={pm.id}
              aria-selected={isSelected}
              onClick={() => onSelect(pm.id)}
              style={{
                cursor: "pointer",
                background: isSelected ? colors.background : "transparent",
              }}
            >
              <td style={tdStyle}>
                <div style={{ fontWeight: "bold" }}>{pm.id}</div>
                <div style={{ fontSize: 13 }}>{pm.procedure}</div>
              </td>
              <td style={tdStyle}>
                <div>{pm.equipmentTag}</div>
                {pm.area ? <div style={{ color: colors.textMuted, fontSize: 12 }}>{pm.area}</div> : null}
              </td>
              <td style={tdStyle}>
                <Badge variant={frequencyBadgeVariant(pm.frequency)}>{frequencyLabel(pm.frequency)}</Badge>
              </td>
              <td style={tdStyle}>{pm.nextDue}</td>
              <td style={tdStyle}>{pm.lastPerformed ?? "Not yet performed"}</td>
              <td style={tdStyle}>{pm.assignedTechnician}</td>
              <td style={tdStyle}>
                <Badge variant={statusBadgeVariant(pm.status)}>{pm.status}</Badge>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
