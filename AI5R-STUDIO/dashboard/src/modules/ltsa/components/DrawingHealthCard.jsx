import { Badge, Card, EmptyState, ProgressBar } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { buildDrawingHealth } from "../utils/drawingMapping";

function Row({ label, children }) {
  return (
    <div style={{ marginBottom: spacing.sm, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ color: colors.textMuted, fontSize: 12 }}>{label}</span>
      <span style={{ color: colors.text }}>{children}</span>
    </div>
  );
}

function yesNoBadge(value) {
  return <Badge variant={value ? "success" : "warning"}>{value ? "Available" : "Not available"}</Badge>;
}

/**
 * Drawing Health (RC-003B §1). Reuses the existing Card pattern
 * (drawing-workspace-spec.html §09 DrawingHealthCard, deepened per the
 * approved Knowledge Hub refinement §10) -- one Card, twelve indicators,
 * each a deterministic sample calculation (buildDrawingHealth,
 * utils/drawingMapping.js), never a fabricated or AI-generated value.
 */
export default function DrawingHealthCard({ drawing }) {
  if (!drawing) {
    return (
      <Card title="Drawing Health">
        <EmptyState
          title="No drawing health to show"
          description="Drawing health appears here once a drawing is opened."
        />
      </Card>
    );
  }

  const health = buildDrawingHealth(drawing);

  return (
    <Card title="Drawing Health">
      <Row label="Revision Status">
        <Badge variant={health.revisionStatus === "APPROVED" ? "success" : health.revisionStatus === "OBSOLETE" ? "danger" : "warning"}>
          {health.revisionStatus}
        </Badge>
      </Row>
      <Row label="Approval Status">
        <Badge variant={health.approvalStatus === "APPROVED" ? "success" : "warning"}>{health.approvalStatus}</Badge>
      </Row>
      <Row label="Latest Revision Date">{health.latestRevisionDate ?? "Unavailable"}</Row>

      <div style={{ marginBottom: spacing.sm }}>
        <ProgressBar
          value={health.drawingCompleteness}
          max={100}
          label={`Drawing Completeness — ${health.drawingCompleteness}%`}
        />
      </div>

      <Row label="Related Documents">{health.relatedDocumentsCount}</Row>
      <Row label="Reference Availability">{yesNoBadge(health.referenceAvailability)}</Row>
      <Row label="BOM Availability">{yesNoBadge(health.bomAvailability)}</Row>
      <Row label="OEM Information">{yesNoBadge(health.oemInformation)}</Row>
      <Row label="Seal Components">{yesNoBadge(health.sealComponentsAvailable)}</Row>
      <Row label="Knowledge Status">
        <Badge variant={health.knowledgeStatus === "Complete" ? "success" : health.knowledgeStatus === "Partial" ? "warning" : "danger"}>
          {health.knowledgeStatus}
        </Badge>
      </Row>
      <Row label="Drawing Quality">
        <Badge variant={health.drawingQuality === "Good" ? "success" : "warning"}>{health.drawingQuality}</Badge>
      </Row>

      <div>
        <ProgressBar
          value={health.engineeringConfidence}
          max={100}
          label={`Engineering Confidence — ${health.engineeringConfidence}% (sample calculation, not Engineering AI)`}
        />
      </div>
    </Card>
  );
}
