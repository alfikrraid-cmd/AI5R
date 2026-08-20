import { Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value ?? "Unavailable"}</div>
    </div>
  );
}

/**
 * OEM Knowledge Layer (RC-003B §3). Reuses the same label/value Field
 * pattern already established by DrawingMetadataPanel/PumpDetailPanel/
 * SealDetailPanel (Card is the shared component; the tiny inline `Field`
 * row is each panel's own local presentational primitive by existing
 * repo convention, not a second Metadata Panel).
 */
export default function OEMKnowledgePanel({ drawing }) {
  if (!drawing) {
    return (
      <Card title="OEM Knowledge">
        <EmptyState
          title="No OEM information to show"
          description="OEM knowledge appears here once a drawing is opened."
        />
      </Card>
    );
  }

  const oem = drawing.oem;

  if (!oem) {
    return (
      <Card title="OEM Knowledge">
        <EmptyState
          title="No OEM information recorded"
          description="This drawing has no OEM knowledge linked yet."
        />
      </Card>
    );
  }

  return (
    <Card title="OEM Knowledge">
      <Field label="OEM" value={oem.oem} />
      <Field label="Manufacturer" value={oem.manufacturer} />
      <Field label="Model" value={oem.model} />
      <Field label="Series" value={oem.series} />
      <Field label="Seal Type" value={oem.sealType} />
      <Field label="Material" value={oem.material} />
      <Field label="Operating Limits" value={oem.operatingLimits} />
      <Field label="Application Notes" value={oem.applicationNotes} />
    </Card>
  );
}
