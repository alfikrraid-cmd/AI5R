import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { criticalityBadgeVariant, statusBadgeVariant } from "../utils/pumpHealth";

// MWO-LTSA-UI-V2-001 -- "Health Score" and "Next PM" are removed: both are
// permanently null in mapPumpRecord (no scoring algorithm and no PM
// Schedule capability exist anywhere in this codebase, per ADR-PUMP-001)
// yet this table rendered them as if real -- healthScoreColor(null) always
// fell through to the "danger" red tier, so every single row showed a red
// "null" badge regardless of actual pump condition. That is fabricated-
// looking noise, not a real signal, found during the Open Design audit.
// Criticality replaces Health Score: a real, already-fetched field
// (pump.criticality) with no prior column here at all.
const HEADERS = ["Pump", "Area", "Criticality", "Open Work Orders", "Status"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
  position: "sticky",
  top: 0,
  background: colors.panel,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function PumpRegistryTable({ pumps, selectedCode, onSelect }) {
  if (pumps.length === 0) {
    return (
      <EmptyState
        title="No pumps match"
        description="Adjust the search text or status filter to see registry results."
      />
    );
  }

  function handleKeyDown(event, code) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(code);
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
          {pumps.map((pump) => {
            const isSelected = pump.code === selectedCode;

            return (
              <tr
                key={pump.code}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(pump.code)}
                onKeyDown={(event) => handleKeyDown(event, pump.code)}
                style={{
                  cursor: "pointer",
                  // MWO-LTSA-UI-V2-001 -- colors.background (#0B1020) is
                  // near-identical to the table's own implicit dark
                  // background, so the selected row was barely
                  // distinguishable (visual self-review finding: "is the
                  // selected asset obvious?"). colors.panel (a real,
                  // already-defined token, not a new color) plus a left
                  // accent border make selection unambiguous at a glance.
                  background: isSelected ? colors.panel : "transparent",
                  borderLeft: isSelected ? `3px solid ${colors.info}` : "3px solid transparent",
                }}
              >
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{pump.tag}</div>
                  <div style={{ fontSize: 13 }}>{pump.name}</div>
                  <div style={{ color: colors.textMuted, fontSize: 12 }}>{pump.manufacturer}</div>
                </td>
                <td style={tdStyle}>{pump.area}</td>
                <td style={tdStyle}>
                  {pump.criticality ? (
                    <Badge variant={criticalityBadgeVariant(pump.criticality)}>{pump.criticality}</Badge>
                  ) : (
                    <span style={{ color: colors.textMuted }}>—</span>
                  )}
                </td>
                <td style={tdStyle}>{pump.openWO}</td>
                <td style={tdStyle}>
                  <Badge variant={statusBadgeVariant(pump.status)}>{pump.status}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
