import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  failureCategoryLabel,
  priorityBadgeVariant,
  severityBadgeVariant,
  statusBadgeVariant,
  statusLabel,
} from "../utils/cmStatus";

const HEADERS = [
  "CM ID",
  "Equipment",
  "Failure Category",
  "Severity",
  "Priority",
  "Downtime",
  "Assigned Technician",
  "Status",
];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function CMReportTable({ cmReports, selectedId, onSelect }) {
  if (cmReports.length === 0) {
    return (
      <EmptyState
        title="No corrective maintenance reports match"
        description="Adjust the search text or status filter to see registry results."
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
          {cmReports.map((cm) => {
            const isSelected = cm.id === selectedId;

            return (
              <tr
                key={cm.id}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(cm.id)}
                onKeyDown={(event) => handleKeyDown(event, cm.id)}
                style={{
                  cursor: "pointer",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{cm.id}</div>
                  <div style={{ fontSize: 13 }}>{cm.failureDescription}</div>
                </td>
                <td style={tdStyle}>
                  <div>{cm.equipmentTag}</div>
                  {cm.area ? <div style={{ color: colors.textMuted, fontSize: 12 }}>{cm.area}</div> : null}
                </td>
                <td style={tdStyle}>{failureCategoryLabel(cm.failureCategory)}</td>
                <td style={tdStyle}>
                  <Badge variant={severityBadgeVariant(cm.severity)}>{cm.severity}</Badge>
                </td>
                <td style={tdStyle}>
                  <Badge variant={priorityBadgeVariant(cm.priority)}>{cm.priority}</Badge>
                </td>
                <td style={tdStyle}>{cm.downtimeHours} hrs</td>
                <td style={tdStyle}>{cm.assignedTechnician}</td>
                <td style={tdStyle}>
                  <Badge variant={statusBadgeVariant(cm.status)}>{statusLabel(cm.status)}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
