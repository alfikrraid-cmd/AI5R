/**
 * Pure derivation helpers for the Document Workspace (RC-004). Same
 * "pure function over already-loaded sample data" pattern as
 * drawingMapping.js (the canonical reference this RC reuses) --
 * pumpHealth.js/workOrderStatus.js before it.
 */

const STATUS_VARIANT = {
  APPROVED: "success",
  IN_REVIEW: "warning",
  DRAFT: "info",
  OBSOLETE: "danger",
};

// MWO-LTSA-052 -- single source of truth for the Document Library's type
// list, extracted here since DocumentLibraryPanel.jsx's "Type" select and
// DocumentReferencePanel.jsx's chip row previously each defined their own
// identical copy. "Datasheet" is the one addition this MWO names that
// wasn't already covered by an existing type (Certificate/Installation
// Guide/OEM Documentation/Inspection Report already cover this MWO's
// Certificates/Installation Manual/OEM Manual/Inspection Report terms
// under their existing names -- not renamed, to avoid unnecessary churn
// across sample data and tests for a cosmetic vocabulary difference).
// "Drawing" is deliberately not a document type here: DocumentViewerPanel.jsx's
// own header comment already establishes Drawing and Document as separate,
// sibling workspaces ("a Document may reference an equipment's drawing but
// a Drawing never references a document") -- adding it as a type would
// contradict that existing, disclosed architectural boundary.
export const DOCUMENT_TYPES = [
  "Manual",
  "OEM Documentation",
  "Installation Guide",
  "Maintenance Procedure",
  "Inspection Report",
  "Technical Bulletin",
  "Certificate",
  "Specification",
  "Datasheet",
];

export function documentStatusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export const RECENT_DOCUMENTS_LIMIT = 5;

/**
 * Document Library scope: All / Recent / Favorites (drawing-workspace-spec.html
 * §09 LibraryScopeTabs, not present in the Drawing Foundation's own
 * DrawingLibraryPanel -- reused here from the original Open Design
 * reference rather than invented fresh for Document).
 */
export function applyLibraryScope(documents, scope) {
  if (scope === "favorites") {
    return documents.filter((document) => document.favorite);
  }
  if (scope === "recent") {
    return [...documents]
      .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0))
      .slice(0, RECENT_DOCUMENTS_LIMIT);
  }
  return documents;
}

export function matchesDocumentSearch(document, term) {
  if (!term) {
    return true;
  }

  const haystack = `${document.equipmentTag ?? ""} ${document.documentNumber} ${document.title} ${document.documentType}`.toLowerCase();
  return haystack.includes(term.toLowerCase());
}

export function matchesDocumentType(document, documentType) {
  return !documentType || document.documentType === documentType;
}

/**
 * Folder tree grouping: two top-level groups (Reference Documents,
 * Equipment Documents), the latter further grouped by equipment tag --
 * same grouping primitive as drawingMapping.js's groupDrawingsByEquipment,
 * applied only within the Equipment category.
 */
export function groupDocumentsByCategory(documents) {
  const reference = documents.filter((document) => document.category === "Reference");
  const equipmentDocuments = documents.filter((document) => document.category === "Equipment");

  const order = [];
  const byTag = new Map();
  for (const document of equipmentDocuments) {
    if (!byTag.has(document.equipmentTag)) {
      byTag.set(document.equipmentTag, []);
      order.push(document.equipmentTag);
    }
    byTag.get(document.equipmentTag).push(document);
  }

  return {
    reference,
    equipment: order.map((equipmentTag) => ({ equipmentTag, documents: byTag.get(equipmentTag) })),
  };
}

export function findCurrentDocumentRevision(document) {
  return document.revisions.find((revision) => revision.current) ?? null;
}

/**
 * MWO-LTSA-062 -- Document Workspace, production persistence path. Maps
 * the real seal_engineering_document row (the same table/gateway/n8n
 * workflow Drawing Workspace already reads, unfiltered here -- every
 * document_type, not just DRAWING) into the shape DocumentOpenDesignView.jsx/
 * DocumentLibraryPanel.jsx already expect, the same "Raw Backend -> Mapping
 * -> Open Design" philosophy pumpMapping.js/sealMapping.js/pmMapping.js/
 * cmMapping.js/drawingMapping.js/installationMapping.js all already
 * establish.
 *
 * Honest, disclosed simplifications from sampleDocuments.js's fictional
 * richness (never fabricated, matching Drawing's own MWO-LTSA-051A
 * precedent for the identical situation):
 * - documentType passes through the real document_type enum value
 *   verbatim (e.g. "INSTALLATION_GUIDE") -- it does NOT translate into
 *   DOCUMENT_TYPES' Title-Case vocabulary ("Installation Guide"), since no
 *   real, evidenced mapping between the two exists; inventing one would be
 *   fabricated metadata. This means DocumentReferencePanel's type chips
 *   (built from DOCUMENT_TYPES) will not visually match a real document's
 *   raw type value -- a disclosed, known gap, not silently papered over.
 * - category ("Equipment" vs "Reference", the Document Library's two
 *   top-level tree groups) is a real, non-fabricated derivation: a
 *   document is "Equipment" only if its seal_code resolves to at least one
 *   compatible pump via seal_pump_compatibility (compatibilityRecords,
 *   the same getSealCompatibility() data Seal.jsx/Drawing already use),
 *   otherwise "Reference". equipmentTag is the first such compatible pump
 *   tag, or null.
 * - discipline and favorite have no real column/source -- discipline stays
 *   null, favorite stays false, never guessed.
 * - revisions is derived as at most one entry from the record's own
 *   revision/issue_date/description fields when no sibling rows are
 *   known -- the exact same "never fabricate Rev A/B/C" discipline
 *   drawingMapping.js's mapDrawingRecord already established. author/
 *   checker/approvedBy/approvalStatus have no real column and stay null.
 *
 * MWO-LTSA-072 -- Engineering Document Management. Adds real, previously-
 * unmapped columns (fileReference/fileName/fileFormat/pageCount/
 * manufacturer/language) -- no schema change, these columns already exist
 * on seal_engineering_document (BP-SEAL-ENGINEERING-DOCUMENT), simply
 * never read by mapDocumentRecord() before this MWO. `allRecords`
 * (optional, defaults to []) enables real multi-row Version/Revision
 * history: per BP-SEAL-ENGINEERING-DOCUMENT's own README/product.manifest
 * ("Engineering Documents are immutable... a new revision must be
 * registered as a new document_code row" -- Architecture Decision item 7,
 * MWO-030/040B), the canonical revision-history model is MULTIPLE rows
 * sharing one document_number, not a history array on one row. When
 * `allRecords` is omitted (every pre-072 caller/test), behavior is
 * unchanged: at most one derived revision entry from the record's own
 * fields. When sibling rows sharing document_number ARE known, they
 * replace the single-entry fallback with real, un-fabricated multi-row
 * history, newest issue_date marked current.
 */
export function mapDocumentRecord(record, compatibilityRecords, allRecords = []) {
  const compatiblePumps = compatibilityRecords
    .filter((item) => item.seal_code === record.seal_code)
    .map((item) => item.pump_tag_number);

  const revisions = resolveDocumentVersions(record, allRecords);

  return {
    id: record.document_code,
    title: record.title ?? null,
    documentNumber: record.document_number ?? null,
    documentType: record.document_type ?? null,
    category: compatiblePumps.length > 0 ? "Equipment" : "Reference",
    equipmentTag: compatiblePumps[0] ?? null,
    sealCode: record.seal_code ?? null,
    discipline: null,
    status: record.status ?? null,
    currentRevision: record.revision ?? null,
    createdAt: record.created_at ?? null,
    updatedAt: record.updated_at ?? null,
    favorite: false,
    revisions,
    // MWO-LTSA-072 -- real, previously-unmapped seal_engineering_document
    // columns, needed for Preview/Download/Metadata/Engineering Attachment.
    fileReference: record.file_reference ?? null,
    fileName: record.file_name ?? null,
    fileFormat: record.file_format ?? null,
    pageCount: record.page_count ?? null,
    manufacturer: record.manufacturer ?? null,
    language: record.language ?? null,
  };
}

/**
 * MWO-LTSA-072 -- real multi-row Version/Revision resolution. `allRecords`
 * is the raw (snake_case, pre-mapDocumentRecord) list this document was
 * fetched alongside -- siblings are every OTHER row sharing the same real
 * document_number (never fabricated: a document with no document_number,
 * or no siblings, falls back to at most its own single revision entry,
 * matching the pre-072 behavior exactly). Sorted newest-issue_date-first;
 * that first row is marked current -- a real, disclosed, deterministic
 * rule (not a guess), the same "most recent known fact wins" precedent
 * drawingMapping.js's own single-entry `current: true` already uses.
 */
export function resolveDocumentVersions(record, allRecords) {
  const siblings = record.document_number
    ? allRecords.filter((candidate) => candidate.document_number === record.document_number)
    : [];

  const pool = siblings.length > 0 ? siblings : record.revision ? [record] : [];

  const sorted = [...pool].sort((a, b) => {
    const dateA = a.issue_date ?? "";
    const dateB = b.issue_date ?? "";
    return dateA < dateB ? 1 : dateA > dateB ? -1 : 0;
  });

  return sorted.map((row, index) => ({
    revision: row.revision ?? null,
    date: row.issue_date ?? null,
    author: null,
    checker: null,
    approvedBy: null,
    approvalStatus: null,
    description: row.description ?? null,
    current: index === 0,
    obsolete: index !== 0,
  }));
}

/**
 * MWO-LTSA-072 -- Preview/Download capability check. seal_engineering_document's
 * own README/product.manifest is explicit: "file_reference is a
 * pointer/path field, not a storage backend" (Architecture Decision item
 * 7, MWO-030) -- there is no S3 client, blob storage, or file server
 * anywhere in this codebase (confirmed by repository archaeology before
 * this MWO). A pointer like "s3://bucket/doc.pdf" is real data but is NOT
 * directly retrievable by a browser -- rendering a "working" Preview/
 * Download button for it would be fabricating a capability this system
 * doesn't have. Only an http(s) URL is something a browser can actually
 * open/download without a new backend -- so that is the one, narrow,
 * honest bar for "available". Anything else (null, s3://, a bare
 * filename) is honestly reported as unavailable.
 */
export function isFilePreviewAvailable(document) {
  return typeof document.fileReference === "string" && /^https?:\/\//i.test(document.fileReference);
}

export const isFileDownloadAvailable = isFilePreviewAvailable;
