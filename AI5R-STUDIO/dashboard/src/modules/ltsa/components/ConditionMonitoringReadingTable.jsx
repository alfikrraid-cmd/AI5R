import { Badge } from "../../../design-system";
import { WorkflowStatusBadge } from "./WorkflowStatusBadge";

/**
 * UI-D3.2 -- Condition Monitoring Reading registry table
 *
 * Compact engineering table prioritizing:
 * - Reading ID
 * - Equipment / Asset (asset-centric, supporting PUMP, LIQUID RING COMPRESSOR, UNCLASSIFIED, etc.)
 * - Area
 * - Reading Date
 * - Workflow Status
 * - Seal Leak (real leak booleans, not fabricated severity)
 * - Mechseal Temp (DE / NDE)
 * - Finding
 *
 * Responsive mobile:
 * - Controlled horizontal scroll or compact card list under mobile breakpoint.
 * - Zero body overflow.
 */

function truncate(text, max = 50) {
  if (!text) return "—";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function tempPair(reading) {
  const de = reading.mechsealTempDe != null ? `${reading.mechsealTempDe}` : "—";
  const nde = reading.mechsealTempNde != null ? `${reading.mechsealTempNde}` : "—";
  return `${de} / ${nde} °C`;
}

function handleKeyDown(event, id, onSelect) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelect(id);
  }
}

export default function ConditionMonitoringReadingTable({
  readings,
  selectedId,
  onSelect,
  mobileCollapsed = false,
  onExpand,
}) {
  if (readings.length === 0) {
    return (
      <div className="cmon-empty-state">
        <p className="cmon-empty-title">No Condition Monitoring readings match</p>
        <p className="cmon-empty-description">Adjust the search text or filters to see registry results.</p>
      </div>
    );
  }

  const selectedReading = readings.find((reading) => reading.id === selectedId) ?? null;

  return (
    <div className="cmon-registry" data-collapsed={mobileCollapsed && !!selectedReading ? "true" : "false"}>
      {/* Desktop: compact engineering table */}
      <div className="cmon-table-wrap">
        <table className="cmon-table">
          <thead>
            <tr>
              <th>Reading ID</th>
              <th>Equipment / Asset</th>
              <th>Area</th>
              <th>Reading Date</th>
              <th>Workflow Status</th>
              <th>Seal Leak</th>
              <th>Mechseal Temp (DE / NDE)</th>
              <th>Finding</th>
            </tr>
          </thead>

          <tbody>
            {readings.map((reading) => {
              const isSelected = reading.id === selectedId;
              const leakDetected = Boolean(reading.leakDe || reading.leakNde);
              const hasLeakInfo =
                (reading.leakDe !== null && reading.leakDe !== undefined) ||
                (reading.leakNde !== null && reading.leakNde !== undefined);
              const leakLabel = leakDetected ? "Leak Detected" : hasLeakInfo ? "No Leak" : "Not Recorded";

              return (
                <tr
                  key={reading.id}
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => onSelect(reading.id)}
                  onKeyDown={(event) => handleKeyDown(event, reading.id, onSelect)}
                >
                  <td>
                    <span className="cmon-id">{reading.id}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{reading.equipmentTag ?? "N/A"}</span>
                  </td>
                  <td>{reading.area ?? "N/A"}</td>
                  <td>{reading.readingDate ?? "N/A"}</td>
                  <td>
                    <WorkflowStatusBadge status={reading.workflowStatus} />
                  </td>
                  <td>
                    <Badge variant={leakDetected ? "danger" : hasLeakInfo ? "success" : "neutral"}>
                      {leakLabel}
                    </Badge>
                  </td>
                  <td>{tempPair(reading)}</td>
                  <td>{truncate(reading.finding)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile: compact card list, same data/selection/keyboard behavior */}
      <div className="cmon-card-list">
        {readings.map((reading) => {
          const isSelected = reading.id === selectedId;
          const leakDetected = Boolean(reading.leakDe || reading.leakNde);
          const hasLeakInfo =
            (reading.leakDe !== null && reading.leakDe !== undefined) ||
            (reading.leakNde !== null && reading.leakNde !== undefined);
          const leakLabel = leakDetected ? "Leak Detected" : hasLeakInfo ? "No Leak" : "Not Recorded";

          return (
            <div
              key={reading.id}
              className="cmon-card"
              role="button"
              aria-selected={isSelected}
              tabIndex={0}
              onClick={() => onSelect(reading.id)}
              onKeyDown={(event) => handleKeyDown(event, reading.id, onSelect)}
            >
              <div className="cmon-card-top">
                <div>
                  <div className="cmon-id">{reading.id}</div>
                  <div className="cmon-subtext">{reading.readingDate ?? "N/A"}</div>
                </div>
                <WorkflowStatusBadge status={reading.workflowStatus} />
              </div>
              <div className="cmon-card-meta">
                <span>
                  <strong>{reading.equipmentTag ?? "N/A"}</strong>
                  {reading.area ? ` · ${reading.area}` : ""}
                </span>
                <Badge variant={leakDetected ? "danger" : hasLeakInfo ? "success" : "neutral"}>
                  {leakLabel}
                </Badge>
              </div>
              <div className="cmon-card-meta">
                <span>Mechseal: {tempPair(reading)}</span>
              </div>
              {reading.finding && <div className="cmon-subtext">{truncate(reading.finding, 80)}</div>}
            </div>
          );
        })}
      </div>

      {/* Mobile, post-selection: collapsed summary + explicit expand button */}
      {selectedReading && (
        <div className="cmon-collapsed-summary">
          <div className="cmon-collapsed-info">
            <span className="cmon-id">{selectedReading.id}</span>
            <span className="cmon-subtext">{selectedReading.readingDate ?? "N/A"}</span>
            <WorkflowStatusBadge status={selectedReading.workflowStatus} />
          </div>
          <button type="button" className="cmon-collapsed-expand" onClick={onExpand}>
            View All Condition Monitoring
          </button>
        </div>
      )}
    </div>
  );
}
