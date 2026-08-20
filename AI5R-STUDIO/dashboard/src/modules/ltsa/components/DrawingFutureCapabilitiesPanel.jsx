import { Badge, Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const FUTURE_CAPABILITIES = ["AI Analysis", "Relationship Graph", "Digital Twin", "OCR", "Knowledge Graph"];

/**
 * RC-003B "PLACEHOLDER ONLY" section. Reuses the exact same dashed-card +
 * "Reserved" badge visual language already established for reserved
 * surfaces elsewhere in LTSA (e.g. Executive Dashboard's
 * EngineeringInsightPanel/BusinessOpportunityPanel/DigitalTwinPanel).
 * No data is fabricated for any of these five -- each renders only its
 * name and "Future Capability".
 */
export default function DrawingFutureCapabilitiesPanel() {
  return (
    <Card title="Future Capabilities">
      <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
        {FUTURE_CAPABILITIES.map((capability) => (
          <div
            key={capability}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              border: `1px dashed ${colors.border}`,
              borderRadius: 8,
              padding: spacing.sm,
            }}
          >
            <span style={{ color: colors.text }}>{capability}</span>
            <Badge variant="info">Future Capability</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
