import { Badge } from "../../../design-system";
import { priorityBadgeVariant, statusBadgeVariant, statusLabel } from "../utils/workOrderStatus";

/**
 * UI-D2A -- Work Order Workspace reference rebuild. Restyled from the old
 * dark design-system table (colors.js/spacing.js, illegible once the page
 * shell around it went light) to the same light `.ltsa-open-design` token
 * scope WorkOrderOpenDesignView already uses -- one consistent visual
 * language across the whole Work Order page, not a second competing one.
 * Badge is kept as-is: its own colored-pill background stays legible on
 * either a dark or light surface, confirmed on Pump/Seal's own registry
 * tables already. Columns, data, selection, and keyboard behavior are
 * byte-identical to before -- this is a visual pass only.
 *
 * UI-D2A.1 -- Chief's feedback: the 6-column dense table must not be
 * squeezed into narrow columns on mobile. Two additional representations
 * of the SAME data/selection/keyboard behavior are rendered alongside the
 * desktop table, chosen purely by CSS (`@media` in WorkOrder.css, mirrors
 * this codebase's existing "CSS decides, markup stays" responsive
 * convention -- e.g. WorkOrderTabStrip/sidebar):
 * - `.workorder-card-list` -- one compact card per work order (WO ID +
 *   title, Equipment, Priority badge, Status badge, Assigned Technician,
 *   Due Date), shown instead of the table under the mobile breakpoint.
 * - `.workorder-collapsed-summary` -- shown instead of the full card list
 *   once a work order is selected on mobile (`mobileCollapsed` prop, only
 *   ever true when the caller is also on a narrow viewport -- desktop CSS
 *   hides this element unconditionally, per Chief's "desktop table always
 *   stays dense" instruction), so the user reaches the detail view
 *   without scrolling past the whole registry first. `onExpand` is the
 *   "View All Work Orders" escape hatch back to the full list -- registry
 *   access is never removed, only collapsed.
 */
const HEADERS = ["Work Order", "Equipment", "Priority", "Assigned Technician", "Due Date", "Status"];

function handleKeyDown(event, id, onSelect) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelect(id);
  }
}

export default function WorkOrderRegistryTable({ workOrders, selectedId, onSelect, mobileCollapsed = false, onExpand }) {
  if (workOrders.length === 0) {
    return (
      <div className="workorder-empty-state">
        <p className="workorder-empty-title">No work orders match</p>
        <p className="workorder-empty-description">Adjust the search text or status filter to see registry results.</p>
      </div>
    );
  }

  const selectedWorkOrder = workOrders.find((workOrder) => workOrder.id === selectedId) ?? null;

  return (
    <div className="workorder-registry" data-collapsed={mobileCollapsed && !!selectedWorkOrder ? "true" : "false"}>
      {/* Desktop: always-dense table (unaffected by mobileCollapsed). */}
      <div className="workorder-table-wrap">
        <table className="workorder-table">
          <thead>
            <tr>
              {HEADERS.map((header) => (
                <th key={header}>{header}</th>
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
                  onKeyDown={(event) => handleKeyDown(event, workOrder.id, onSelect)}
                >
                  <td>
                    <div className="wo-id">{workOrder.id}</div>
                    <div className="wo-title">{workOrder.title}</div>
                  </td>
                  <td>
                    <div>{workOrder.equipmentTag ?? "N/A"}</div>
                    <div className="wo-area">{workOrder.area ?? "N/A"}</div>
                  </td>
                  <td>
                    <Badge variant={priorityBadgeVariant(workOrder.priority)}>{workOrder.priority ?? "N/A"}</Badge>
                  </td>
                  <td>{workOrder.assignedTechnician ?? "N/A"}</td>
                  <td>{workOrder.dueDate ?? "N/A"}</td>
                  <td>
                    <Badge variant={statusBadgeVariant(workOrder.status)}>{statusLabel(workOrder.status)}</Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile: compact card list, same data/selection/keyboard behavior. */}
      <div className="workorder-card-list">
        {workOrders.map((workOrder) => {
          const isSelected = workOrder.id === selectedId;

          return (
            <div
              key={workOrder.id}
              className="workorder-card"
              role="button"
              aria-selected={isSelected}
              tabIndex={0}
              onClick={() => onSelect(workOrder.id)}
              onKeyDown={(event) => handleKeyDown(event, workOrder.id, onSelect)}
            >
              <div className="workorder-card-top">
                <div>
                  <div className="wo-id">{workOrder.id}</div>
                  <div className="wo-title">{workOrder.title}</div>
                </div>
                <Badge variant={statusBadgeVariant(workOrder.status)}>{statusLabel(workOrder.status)}</Badge>
              </div>
              <div className="workorder-card-meta">
                <span>{workOrder.equipmentTag ?? "N/A"}</span>
                <Badge variant={priorityBadgeVariant(workOrder.priority)}>{workOrder.priority ?? "N/A"}</Badge>
              </div>
              <div className="workorder-card-meta">
                <span>{workOrder.assignedTechnician ?? "N/A"}</span>
                <span>Due {workOrder.dueDate ?? "N/A"}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile, post-selection: collapsed summary + explicit escape hatch
          back to the full list -- registry access is never removed. */}
      {selectedWorkOrder && (
        <div className="workorder-collapsed-summary">
          <div className="workorder-collapsed-info">
            <span className="wo-id">{selectedWorkOrder.id}</span>
            <span className="wo-title">{selectedWorkOrder.title}</span>
            <Badge variant={statusBadgeVariant(selectedWorkOrder.status)}>{statusLabel(selectedWorkOrder.status)}</Badge>
          </div>
          <button type="button" className="workorder-collapsed-expand" onClick={onExpand}>
            View All Work Orders
          </button>
        </div>
      )}
    </div>
  );
}
