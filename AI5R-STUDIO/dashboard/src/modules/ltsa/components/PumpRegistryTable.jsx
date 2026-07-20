import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { healthScoreColor, statusBadgeVariant } from "../utils/pumpHealth";

const HEADERS = ["Pump", "Area", "Health Score", "Next PM", "Open Work Orders", "Status"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
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
        {pumps.map((pump) => {
          const isSelected = pump.code === selectedCode;

          return (
            <tr
              key={pump.code}
              aria-selected={isSelected}
              onClick={() => onSelect(pump.code)}
              style={{
                cursor: "pointer",
                background: isSelected ? colors.background : "transparent",
              }}
            >
              <td style={tdStyle}>
                <div style={{ fontWeight: "bold" }}>{pump.tag}</div>
                <div style={{ fontSize: 13 }}>{pump.name}</div>
                <div style={{ color: colors.textMuted, fontSize: 12 }}>{pump.manufacturer}</div>
              </td>
              <td style={tdStyle}>{pump.area}</td>
              <td style={tdStyle}>
                <strong style={{ color: healthScoreColor(pump.healthScore) }}>{pump.healthScore}</strong>
              </td>
              <td style={tdStyle}>{pump.nextPM}</td>
              <td style={tdStyle}>{pump.openWO}</td>
              <td style={tdStyle}>
                <Badge variant={statusBadgeVariant(pump.status)}>{pump.status}</Badge>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
