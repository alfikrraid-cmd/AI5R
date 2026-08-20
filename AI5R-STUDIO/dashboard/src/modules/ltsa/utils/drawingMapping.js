/**
 * Pure derivation helpers for the Drawing Workspace Foundation (RC-003A).
 * No fetch, no state -- same "pure function over already-loaded sample
 * data" pattern as pumpHealth.js/workOrderStatus.js.
 */

const STATUS_VARIANT = {
  APPROVED: "success",
  IN_REVIEW: "warning",
  DRAFT: "info",
  OBSOLETE: "danger",
};

export function drawingStatusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

/**
 * Folder tree grouping: one node per equipment tag, in first-seen order,
 * each carrying its own drawings in original array order. Equivalent to
 * the approved Open Design's "Equipment -> Drawing" IA (drawing-workspace-spec.html §04).
 */
export function groupDrawingsByEquipment(drawings) {
  const order = [];
  const byTag = new Map();

  for (const drawing of drawings) {
    if (!byTag.has(drawing.equipmentTag)) {
      byTag.set(drawing.equipmentTag, []);
      order.push(drawing.equipmentTag);
    }
    byTag.get(drawing.equipmentTag).push(drawing);
  }

  return order.map((equipmentTag) => ({ equipmentTag, drawings: byTag.get(equipmentTag) }));
}

export function findCurrentRevision(drawing) {
  return drawing.revisions.find((revision) => revision.current) ?? null;
}

export function isDrawingObsolete(drawing) {
  return findCurrentRevision(drawing)?.obsolete === true;
}

/**
 * Drawing Health (RC-003B). Every indicator below is a deterministic
 * derivation over the drawing's own already-loaded fields -- the same
 * "sample calculation" discipline already established by
 * buildMaintenanceHealth()'s PM Compliance rate (utils/executiveDashboard.js).
 * None of this is Engineering AI: no inference, no model call, no
 * judgment beyond a fixed, disclosed formula.
 */
/**
 * MWO-LTSA-051A -- maps the real Knowledge endpoint drawing shape
 * (LTSAKnowledgeService._build_drawings(): drawing_id/title/
 * document_number/revision/status/file_name/uploaded_at, exposed via the
 * already-real GET /api/ltsa/pumps/{tag}/knowledge endpoint's `drawings`
 * field) into the shape DrawingLibraryPanel/DrawingMetadataPanel/
 * DrawingRevisionPanel/DrawingViewerPanel/buildDrawingHealth already
 * expect. No new backend, API, or SQL -- this is a pure client-side
 * reshape of an existing response, the same "field-mapping utility"
 * pattern pumpMapping.js/sealMapping.js already establish.
 *
 * equipmentTag comes from the real pump tag this record was fetched
 * under (the caller's navContext.assetTag), not from the record itself
 * -- the Knowledge endpoint's drawing rows carry no equipment_tag column,
 * so this is a known, real fact rather than a guess.
 *
 * drawingType/apiPlan/oem have no real data source on this endpoint and
 * stay null, never fabricated. bom/relatedDocuments default to []
 * rather than null (unlike oem) because DrawingBomTable and
 * buildDrawingHealth call `.length` on them directly -- an honest empty
 * array, not a semantic downgrade from "null = unknown".
 *
 * revisions is derived as at most one entry from the record's own
 * revision/uploaded_at pair -- the real data source has no revision
 * history table, only "the current revision of this document", so a
 * multi-row Rev A/B/C history is never fabricated.
 *
 * MWO-LTSA-062 -- sealModel/relatedDocuments, optional third-arg
 * overrides (default {} preserves every pre-062 caller/test exactly:
 * sealModel stays null, relatedDocuments stays [] when omitted). The
 * Knowledge endpoint's drawing rows carry no seal_code (a frozen,
 * deliberately narrow shape -- see MWO-LTSA-033's own test
 * "maps_only_the_seven_required_metadata_fields", which this MWO does
 * not reopen), so both are resolved by the CALLER at the pump level
 * instead: DrawingWorkspace.jsx resolves this pump's compatible seal_code(s)
 * via the existing getSealCompatibility()/resolveCompatibleSeals()
 * (sealMapping.js), looks up their real model via the existing getSeals(),
 * and separately fetches getDocuments() (the same real
 * seal_engineering_document list Document Workspace now reads) filtered
 * to those seal_code(s) and document_type !== 'DRAWING'. Both stay at
 * their honest pre-062 default when the caller has nothing real to pass.
 */
export function mapDrawingRecord(record, equipmentTag, { sealModel = null, relatedDocuments = [] } = {}) {
  const revisions = record.revision
    ? [
        {
          revision: record.revision,
          date: record.uploaded_at ?? null,
          author: null,
          checker: null,
          approvedBy: null,
          description: null,
          approvalStatus: null,
          current: true,
          obsolete: false,
        },
      ]
    : [];

  return {
    id: record.drawing_id,
    title: record.title ?? null,
    drawingNumber: record.document_number ?? null,
    drawingType: null,
    equipmentTag: equipmentTag ?? null,
    sealModel,
    apiPlan: null,
    currentRevision: record.revision ?? null,
    status: record.status ?? null,
    revisions,
    bom: [],
    oem: null,
    relatedDocuments,
  };
}

export function buildDrawingHealth(drawing) {
  const current = findCurrentRevision(drawing);
  const hasBom = drawing.bom.length > 0;
  const hasOem = Boolean(drawing.oem);
  const hasRelatedDocuments = drawing.relatedDocuments.length > 0;

  const completenessChecks = [
    Boolean(drawing.drawingNumber && drawing.title && drawing.sealModel && drawing.apiPlan),
    hasOem,
    hasBom,
    hasRelatedDocuments,
  ];
  const completeness = Math.round(
    (completenessChecks.filter(Boolean).length / completenessChecks.length) * 100
  );

  const presentCount = [hasBom, hasOem, hasRelatedDocuments].filter(Boolean).length;
  const knowledgeStatus = presentCount === 3 ? "Complete" : presentCount === 0 ? "Minimal" : "Partial";

  const drawingQuality =
    current?.approvalStatus === "APPROVED" && !isDrawingObsolete(drawing) ? "Good" : "Needs Review";

  const approvalScore = current?.approvalStatus === "APPROVED" ? 100 : current?.approvalStatus === "PENDING" ? 50 : 0;
  const obsoleteScore = isDrawingObsolete(drawing) ? 0 : 100;
  const engineeringConfidence = Math.round((completeness + approvalScore + obsoleteScore) / 3);

  return {
    revisionStatus: drawing.status,
    approvalStatus: current?.approvalStatus ?? "UNKNOWN",
    latestRevisionDate: current?.date ?? null,
    drawingCompleteness: completeness,
    relatedDocumentsCount: drawing.relatedDocuments.length,
    referenceAvailability: hasRelatedDocuments,
    bomAvailability: hasBom,
    oemInformation: hasOem,
    sealComponentsAvailable: true,
    knowledgeStatus,
    drawingQuality,
    engineeringConfidence,
  };
}
