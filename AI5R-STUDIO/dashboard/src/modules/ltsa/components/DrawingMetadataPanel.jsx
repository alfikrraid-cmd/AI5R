import { Badge, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { drawingStatusBadgeVariant } from "../utils/drawingMapping";

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return "N/A";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function Field({ label, value, children }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{children !== undefined ? children : (value ?? "Unavailable")}</div>
    </div>
  );
}

/**
 * Drawing Metadata Panel (R9E).
 * Exposes authoritative engineering fields for the active drawing:
 * document number, title, side (DE/NDE), generation, confidence status,
 * applicability, revision, storage availability, and file metadata.
 *
 * SECURITY: Never displays object_key, MinIO bucket, or internal hashes.
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

  const drawingNumber = drawing.drawingNumber || drawing.documentCode || drawing.id;
  const side = drawing.equipmentSide;
  const sideBadgeVariant = side === "DE" ? "info" : side === "NDE" ? "purple" : "neutral";

  return (
    <Card title="Metadata">
      <Field label="Drawing Number" value={drawingNumber} />
      <Field label="Drawing Title" value={drawing.title} />
      <Field label="Drawing Type" value={drawing.drawingType ?? "DRAWING"} />
      <Field label="Equipment Tag" value={drawing.equipmentTag ?? "N/A"} />

      <Field label="Equipment Side">
        {side ? <Badge variant={sideBadgeVariant}>{side}</Badge> : "N/A"}
      </Field>

      <Field label="Mechanical Seal Model" value={drawing.sealModel ?? "N/A"} />
      <Field label="API Plan" value={drawing.apiPlan ?? "N/A"} />
      <Field label="Current Revision" value={drawing.currentRevision ?? "N/A"} />

      <Field label="Drawing Generation">
        <Badge variant="neutral">{drawing.drawingGeneration ?? "STANDARD"}</Badge>
      </Field>

      <Field label="Confidence Status">
        <Badge variant={drawing.confidenceStatus === "CONFIRMED" ? "success" : "warning"}>
          {drawing.confidenceStatus ?? "CONFIRMED"}
        </Badge>
      </Field>

      <Field label="Evidence Method" value={drawing.evidenceMethod ?? "N/A"} />

      <Field label="Drawing Status">
        <Badge variant={drawingStatusBadgeVariant(drawing.status)}>{drawing.status ?? "APPROVED"}</Badge>
      </Field>

      <Field label="File Status">
        <Badge variant={drawing.storageAvailable ? "success" : "neutral"}>
          {drawing.storageAvailable ? "Archived in Storage" : "Reference Only (No File)"}
        </Badge>
      </Field>

      <Field label="Original Filename" value={drawing.fileName ?? "N/A"} />
      <Field label="File Size" value={formatFileSize(drawing.fileSizeBytes)} />
    </Card>
  );
}
