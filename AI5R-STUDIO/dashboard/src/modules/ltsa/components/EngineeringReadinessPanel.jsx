import { Card, ProgressBar } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const CATEGORIES = [
  { key: "pump", label: "Pump" },
  { key: "seal", label: "Mechanical Seal" },
  { key: "drawing", label: "Drawing" },
  { key: "document", label: "Document" },
  { key: "knowledge", label: "Knowledge" },
  { key: "inventory", label: "Inventory" },
];

/**
 * RC-002 (Executive Dashboard React Implementation). Pump and Mechanical
 * Seal readiness are real sample-data percentages (buildEngineeringReadiness,
 * utils/executiveDashboard.js). Drawing, Document, Knowledge, and Inventory
 * have no backend/workspace yet -- their value is `null` and this panel
 * renders a disclosed "Not available" row for them rather than a fabricated
 * percentage, per "Display placeholder metrics if backend unavailable."
 */
export default function EngineeringReadinessPanel({ readiness }) {
  return (
    <Card title="Engineering Readiness">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {CATEGORIES.map(({ key, label }) => {
          const value = readiness[key];
          return (
            <div key={key}>
              {value === null || value === undefined ? (
                <div>
                  <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
                  <div style={{ color: colors.textMuted }}>Not available</div>
                </div>
              ) : (
                <ProgressBar value={value} max={100} label={`${label} — ${value}%`} />
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
