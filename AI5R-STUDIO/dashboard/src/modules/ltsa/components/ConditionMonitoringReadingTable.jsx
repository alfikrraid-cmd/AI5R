import { Badge, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const HEADERS = ["Reading ID", "Equipment", "Date", "Mechseal Temp (DE/NDE)", "Leak", "Schedule"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function ConditionMonitoringReadingTable({ readings, selectedId, onSelect }) {
  if (readings.length === 0) {
    return (
      <EmptyState
        title="No Condition Monitoring readings match"
        description="Adjust the search text to see registry results."
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
          {readings.map((reading) => {
            const isSelected = reading.id === selectedId;
            const leakDetected = reading.leakDe || reading.leakNde;

            return (
              <tr
                key={reading.id}
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => onSelect(reading.id)}
                onKeyDown={(event) => handleKeyDown(event, reading.id)}
                style={{
                  cursor: "pointer",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                <td style={tdStyle}>
                  <div style={{ fontWeight: "bold" }}>{reading.id}</div>
                </td>
                <td style={tdStyle}>
                  <div>{reading.equipmentTag}</div>
                  {reading.area ? (
                    <div style={{ color: colors.textMuted, fontSize: 12 }}>{reading.area}</div>
                  ) : null}
                </td>
                <td style={tdStyle}>{reading.readingDate ?? "—"}</td>
                <td style={tdStyle}>
                  {reading.mechsealTempDe ?? "—"} / {reading.mechsealTempNde ?? "—"}
                </td>
                <td style={tdStyle}>
                  <Badge variant={leakDetected ? "danger" : "success"}>
                    {leakDetected ? "Leak" : "Normal"}
                  </Badge>
                </td>
                <td style={tdStyle}>{reading.scheduleCode ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
