import { Badge, Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const RELATIONSHIP_OBJECTS = [
  "Pump",
  "Mechanical Seal",
  "Document",
  "Inventory",
  "PM",
  "CM",
  "Failure",
  "Work Order",
];

const FUTURE_INTEGRATIONS = [
  "Graphiti",
  "Engineering AI",
  "OCR",
  "Knowledge Graph",
  "Digital Twin",
  "Dashboard",
  "Document Workspace",
  "Inventory Workspace",
];

function ReservedRow({ heading }) {
  return (
    <div style={{ border: `1px dashed ${colors.border}`, borderRadius: 8, padding: spacing.sm, marginBottom: spacing.sm }}>
      <div style={{ fontWeight: "bold", color: colors.text }}>{heading}</div>
    </div>
  );
}

/**
 * Drawing Intelligence (RC-003C, the final Drawing Workspace phase).
 * Exactly one panel, per this RC's own VERIFICATION requirement --
 * every one of the 7 mission sections below is a subsection of this same
 * component/file, not a separate panel each. No AI, OCR, graph engine,
 * Graphiti client, or Digital Twin runtime is implemented anywhere here
 * -- every subsection is a static, disclosed placeholder, reusing the
 * same dashed-card "Reserved"/"Future Capability" visual language RC-003B's
 * DrawingFutureCapabilitiesPanel already established (that component is
 * unchanged by this RC and continues to render alongside this one -- it
 * is RC-003B's own approved 5-item teaser summary, a different, narrower
 * scope than this RC's 6 individually-detailed capability sections plus
 * the broader 8-target Future Integration Panel).
 */
export default function DrawingIntelligencePanel() {
  return (
    <>
      <Card title="AI Analysis">
        <ReservedRow heading="Engineering AI Analysis" />
        <Badge variant="info">Reserved</Badge>{" "}
        <Badge variant="info">Future Capability</Badge>
      </Card>

      <Card title="Relationship Graph">
        <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: spacing.sm }}>
          Static visualization only — no graph engine, no live relationship data.
        </p>
        <div
          data-testid="relationship-graph-static"
          style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}
        >
          {RELATIONSHIP_OBJECTS.map((object) => (
            <span
              key={object}
              style={{
                border: `1px solid ${colors.border}`,
                borderRadius: 16,
                padding: `${spacing.xs}px ${spacing.sm}px`,
                fontSize: 12,
                color: colors.text,
              }}
            >
              ↔ {object}
            </span>
          ))}
        </div>
      </Card>

      <Card title="Knowledge Graph">
        <ReservedRow heading="Knowledge Graph" />
        <Badge variant="info">Reserved</Badge>{" "}
        <Badge variant="info">Future Graphiti Integration</Badge>
      </Card>

      <Card title="OCR">
        <ReservedRow heading="OCR Extraction" />
        <Badge variant="info">Future Capability</Badge>
      </Card>

      <Card title="Drawing Highlight">
        <ReservedRow heading="Future Component Highlight" />
      </Card>

      <Card title="Digital Twin">
        <ReservedRow heading="Future Digital Twin" />
      </Card>

      <Card title="Future Integration Panel">
        <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: spacing.sm }}>
          Summary of future integrations. No live integration exists for any item below.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
          {FUTURE_INTEGRATIONS.map((integration) => (
            <div
              key={integration}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: spacing.xs,
              }}
            >
              <span style={{ color: colors.text }}>{integration}</span>
              <Badge variant="purple">No live integration</Badge>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
