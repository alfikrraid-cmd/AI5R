import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { priorityBadgeVariant, statusBadgeVariant, statusLabel } from "../utils/workOrderStatus";

const HEADERS = ["Work Order", "Equipment", "Priority", "Assigned Technician", "Due Date", "Status"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function WorkOrderRegistryTable({ workOrders, selectedId, onSelect }) {
  if (workOrders.length === 0) {
    return (
      <EmptyState
        title="No work orders match"
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
          {workOrders.map((workOrder) => {
            const isSelected = workOrder.id === selectedId;

            return (
              <tr
                key={workOrder.id}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(workOrder.id)}
                onKeyDown={(event) => handleKeyDown(event, workOrder.id)}
                style={{
                  cursor: "pointer",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{workOrder.id}</div>
                  <div style={{ fontSize: 13 }}>{workOrder.title}</div>
                </td>
                <td style={tdStyle}>
                  <div>{workOrder.equipmentTag}</div>
                  <div style={{ color: colors.textMuted, fontSize: 12 }}>{workOrder.area}</div>
                </td>
                <td style={tdStyle}>
                  <Badge variant={priorityBadgeVariant(workOrder.priority)}>{workOrder.priority}</Badge>
                </td>
                <td style={tdStyle}>{workOrder.assignedTechnician}</td>
                <td style={tdStyle}>{workOrder.dueDate}</td>
                <td style={tdStyle}>
                  <Badge variant={statusBadgeVariant(workOrder.status)}>{statusLabel(workOrder.status)}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
