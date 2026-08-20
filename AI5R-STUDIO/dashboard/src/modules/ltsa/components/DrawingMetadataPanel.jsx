import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { drawingStatusBadgeVariant } from "../utils/drawingMapping";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value ?? "Unavailable"}</div>
    </div>
  );
}

/**
 * Drawing Metadata Panel, Foundation scope (drawing-workspace-spec.html
 * §09 EngineeringDataFields, trimmed to the fields RC-003A actually asks
 * for: "View metadata" -- BOM/Seal Components/Related Objects/Drawing
 * Health are out of scope for this RC).
 */
export default function DrawingMetadataPanel({ drawing }) {
  if (!drawing) {
    return (
      <Card title="Metadata">
        <EmptyState
          title="No metadata to show"
          description="Engineering data appears here once a drawing is opened."
        />
      </Card>
    );
  }

  return (
    <Card title="Metadata">
      <Field label="Drawing Number" value={drawing.drawingNumber} />
      <Field label="Drawing Title" value={drawing.title} />
      <Field label="Drawing Type" value={drawing.drawingType} />
      <Field label="Equipment Tag" value={drawing.equipmentTag} />
      <Field label="Mechanical Seal Model" value={drawing.sealModel} />
      <Field label="API Plan" value={drawing.apiPlan} />
      <Field label="Current Revision" value={drawing.currentRevision} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Drawing Status</div>
        <Badge variant={drawingStatusBadgeVariant(drawing.status)}>{drawing.status}</Badge>
      </div>
    </Card>
  );
}
