import { Badge } from "../../../design-system";
import { frequencyBadgeVariant, frequencyLabel, statusBadgeVariant, statusLabel } from "../utils/pmStatus";

/**
 * UI-D2B -- Preventive Maintenance reference rebuild, following the exact
 * pattern UI-D2A.1 established for Work Order: restyled from the old dark
 * design-system table (colors.js/spacing.js) to the same light
 * `.ltsa-open-design` token scope, plus the same mobile card-list +
 * collapsed-summary representations (WorkOrderRegistryTable.jsx), CSS-
 * gated in PM.css. Columns, data, selection, and keyboard behavior are
 * unchanged -- this is a visual/responsive pass only, same real fields
 * PM.jsx already fetches and maps (pmMapping.js).
 */
const HEADERS = ["PM ID", "Equipment", "Frequency", "Next Due", "Last Performed", "Assigned Technician", "Status"];

function handleKeyDown(event, id, onSelect) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelect(id);
  }
}

export default function PMScheduleTable({ pmSchedules, selectedId, onSelect, mobileCollapsed = false, onExpand }) {
  if (pmSchedules.length === 0) {
    return (
      <div className="pm-empty-state">
        <p className="pm-empty-title">No PM schedules match</p>
        <p className="pm-empty-description">Adjust the search text or status filter to see registry results.</p>
      </div>
    );
  }

  const selectedPM = pmSchedules.find((pm) => pm.id === selectedId) ?? null;

  return (
    <div className="pm-registry" data-collapsed={mobileCollapsed && !!selectedPM ? "true" : "false"}>
      {/* Desktop: always-dense table (unaffected by mobileCollapsed). */}
      <div className="pm-table-wrap">
        <table className="pm-table">
          <thead>
            <tr>
              {HEADERS.map((header) => (
                <th key={header}>{header}</th>
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
                  tabIndex={0}
                  onClick={() => onSelect(pm.id)}
                  onKeyDown={(event) => handleKeyDown(event, pm.id, onSelect)}
                >
                  <td>
                    <div className="pm-id">{pm.id}</div>
                    <div className="pm-title">{pm.procedure}</div>
                  </td>
                  <td>
                    <div>{pm.equipmentTag ?? "N/A"}</div>
                    <div className="pm-area">{pm.area ?? "N/A"}</div>
                  </td>
                  <td>
                    <Badge variant={frequencyBadgeVariant(pm.frequency)}>{frequencyLabel(pm.frequency) ?? "N/A"}</Badge>
                  </td>
                  <td>{pm.nextDue ?? "N/A"}</td>
                  <td>{pm.lastPerformed ?? "Not yet performed"}</td>
                  <td>{pm.assignedTechnician ?? "N/A"}</td>
                  <td>
                    <Badge variant={statusBadgeVariant(pm.status)}>{statusLabel(pm.status)}</Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile: compact card list, same data/selection/keyboard behavior. */}
      <div className="pm-card-list">
        {pmSchedules.map((pm) => {
          const isSelected = pm.id === selectedId;

          return (
            <div
              key={pm.id}
              className="pm-card"
              role="button"
              aria-selected={isSelected}
              tabIndex={0}
              onClick={() => onSelect(pm.id)}
              onKeyDown={(event) => handleKeyDown(event, pm.id, onSelect)}
            >
              <div className="pm-card-top">
                <div>
                  <div className="pm-id">{pm.id}</div>
                  <div className="pm-title">{pm.procedure}</div>
                </div>
                <Badge variant={statusBadgeVariant(pm.status)}>{statusLabel(pm.status)}</Badge>
              </div>
              <div className="pm-card-meta">
                <span>{pm.equipmentTag ?? "N/A"}</span>
                <Badge variant={frequencyBadgeVariant(pm.frequency)}>{frequencyLabel(pm.frequency) ?? "N/A"}</Badge>
              </div>
              <div className="pm-card-meta">
                <span>{pm.assignedTechnician ?? "N/A"}</span>
                <span>Due {pm.nextDue ?? "N/A"}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Mobile, post-selection: collapsed summary + explicit escape hatch
          back to the full list -- registry access is never removed. */}
      {selectedPM && (
        <div className="pm-collapsed-summary">
          <div className="pm-collapsed-info">
            <span className="pm-id">{selectedPM.id}</span>
            <span className="pm-title">{selectedPM.procedure}</span>
            <Badge variant={statusBadgeVariant(selectedPM.status)}>{statusLabel(selectedPM.status)}</Badge>
          </div>
          <button type="button" className="pm-collapsed-expand" onClick={onExpand}>
            View All Preventive Maintenance
          </button>
        </div>
      )}
    </div>
  );
}
