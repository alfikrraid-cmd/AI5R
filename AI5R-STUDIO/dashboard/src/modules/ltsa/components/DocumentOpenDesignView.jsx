import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import DocumentReferencePanel from "./DocumentReferencePanel";
import { Badge, Table } from "../../../design-system";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";
import { findCurrentDocumentRevision, isFilePreviewAvailable, isFileDownloadAvailable } from "../utils/documentMapping";

/**
 * MWO-LTSA-052A -- Document Workspace, migrated to the same Open Design
 * information hierarchy as SealOpenDesignView.jsx (MWO-LTSA-042A, the
 * original) and PumpOpenDesignView.jsx (MWO-LTSA-050, the first
 * migration). This is a migration, not a redesign -- every class here is
 * one LTSAOpenDesign.css already defines (chrome-bar/workspace-grid/
 * identity/assessment-section/info-panel/inspector-rail/rail-section/
 * action-bar), and every shared shape (Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup) is the exact components/open-design/
 * kit Pump and Seal already use, unmodified.
 *
 * MWO-LTSA-052C -- Final enterprise alignment, per the MWO-LTSA-052B
 * audit's two evidenced findings:
 * - Revision History now uses the design-system `Table` (the same
 *   component DrawingRevisionPanel.jsx already uses, per RC-003B's own
 *   "explicitly forbids a duplicate Revision Panel" rule) instead of
 *   RefGroup -- RefGroup could only carry one name + one joined meta
 *   string per revision, hiding per-revision Author/Checker/Approver
 *   that the data model always carried (documentMapping.js's revision
 *   shape is field-for-field identical to Drawing's). No new table
 *   component was created.
 * - The Action Bar gains Open PM / Open CM / Open Work Order, using the
 *   exact `onNavigate(key, { assetTag })` contract Drawing's own
 *   navigation already proves (DrawingNavigationPanel.jsx) and that
 *   PM.jsx/CM.jsx already listen for (their own MWO-LTSA-053/054 header
 *   comments record that the original, since-deleted
 *   DocumentNavigationPanel.jsx already sent this same
 *   onNavigate("pm"/"cm", { assetTag }) call -- this restores that,
 *   it does not invent it). Open Work Order reuses the identical
 *   `{ assetTag }` shape Drawing already sends to "workorder" today.
 *   Inventory remains omitted (no workspace exists for it, unchanged).
 *
 * Domain adaptation from Seal/Pump's hierarchy (documented, not silent):
 * - No live backend exists for Document anywhere in the repository (per
 *   this session's own repository archaeology, confirmed again before
 *   this MWO) -- unlike Pump/Seal, this view receives an already-mapped
 *   `document` object as a prop; it performs no fetch, calls no API, and
 *   Engineering AI is a permanent, disclosed placeholder (never wired to
 *   postEngineeringAI), matching this MWO's explicit "No backend. No
 *   API." rule and the "Reserved / Future Capability" language
 *   DrawingWorkspace.jsx's own Engineering Notes card already uses for
 *   the same reason.
 * - Linked Assets (a SECTION ORDER item with no Pump/Seal equivalent) is
 *   rendered via RefGroup -- the exact same reusable primitive Pump/Seal
 *   already use for every other single/list-shaped fact (Compatible
 *   Seals, Related PM/CM/Work Orders). It is a single-item RefGroup when
 *   `document.equipmentTag` is real, otherwise an honestly empty one --
 *   never a fabricated relationship.
 * - Reference Documents reuses DocumentReferencePanel.jsx's existing chip
 *   row verbatim (`bare` mode, MWO-LTSA-052A addition -- see that file's
 *   own header comment) rather than duplicating its filter logic.
 * - The old persistent Document Viewer (zoom/rotate/pan toolbar) has no
 *   slot in this MWO's SECTION ORDER; its "open and look at this
 *   document" capability is preserved as an on-demand Drawer (reusing
 *   PumpWorkspaceDrawer, the same "Buka Drawing" mechanism Pump/Seal
 *   already use for their own no-backend preview), triggered from the
 *   sticky Action Bar instead of occupying a permanent middle column --
 *   the same static "no rendering backend exists yet" disclosure the old
 *   DocumentViewerPanel.jsx already showed, not a capability removal.
 *
 * MWO-LTSA-072 -- Engineering Document Management. Adds one new Section,
 * "Source Document" (file metadata + Preview/Download), directly after
 * Document Overview. No new storage, no schema change --
 * seal_engineering_document's own file_reference/file_name/file_format/
 * page_count/manufacturer/language columns already existed, simply
 * unmapped before this MWO. Per that table's own README/product.manifest
 * ("file_reference is a pointer/path field, not a storage backend" --
 * Architecture Decision item 7, MWO-030) and confirmed repository
 * archaeology (no S3 client, blob storage, or file server exists
 * anywhere in this codebase), Preview/Download are real, WORKING links
 * only when file_reference is a directly browser-fetchable http(s) URL
 * (isFilePreviewAvailable()/isFileDownloadAvailable(), documentMapping.js)
 * -- otherwise they render the same honest "unavailable" disclosure
 * DrawingViewerPanel.jsx's own "Download (Coming soon)" button and this
 * file's own pre-existing Document Preview Drawer already established,
 * never a fabricated working control for a pointer that isn't
 * retrievable. The existing "View Document →" Action Bar trigger and its
 * Drawer are UNCHANGED in mechanism (same button, same Drawer) -- only
 * the Drawer's CONTENT is now conditionally real.
 * Version/Revision: `document.revisions` may now contain real multiple
 * entries (documentMapping.js's resolveDocumentVersions(), sibling rows
 * sharing document_number -- per BP-SEAL-ENGINEERING-DOCUMENT's own
 * immutability rule, "a new revision must be registered as a new
 * document_code row") -- the existing Revision History Table below is
 * unchanged; it already renders however many rows `revisions` contains.
 */

const STATUS_META = {
  APPROVED: { tier: "normal", label: "Approved" },
  IN_REVIEW: { tier: "attention", label: "In Review" },
  DRAFT: { tier: "attention", label: "Draft" },
  OBSOLETE: { tier: "critical", label: "Obsolete" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Unknown" };
}

// MWO-LTSA-052C -- Revision History column set, per the MWO's own field
// list (Revision/Date/Author/Checker/Approver/Approval Status/
// Description), plus a Status column preserving the Current/Obsolete
// distinction the old RefGroup flag/flagLabel used to carry ("Preserve
// all existing data"). Never fabricates: any null field renders "—".
const REVISION_COLUMNS = [
  { key: "revision", header: "Revision" },
  { key: "date", header: "Date", render: (value) => value ?? "—" },
  { key: "author", header: "Author", render: (value) => value ?? "—" },
  { key: "checker", header: "Checker", render: (value) => value ?? "—" },
  { key: "approvedBy", header: "Approver", render: (value) => value ?? "—" },
  {
    key: "approvalStatus",
    header: "Approval Status",
    render: (value) => (value ? <Badge variant={value === "APPROVED" ? "success" : "warning"}>{value}</Badge> : "—"),
  },
  { key: "description", header: "Description", render: (value) => value ?? "—" },
  {
    key: "current",
    header: "Status",
    render: (value, row) => (value ? <Badge variant="info">Current</Badge> : row.obsolete ? <Badge variant="danger">Obsolete</Badge> : "—"),
  },
];

export default function DocumentOpenDesignView({
  document,
  documentTypeFilter,
  onDocumentTypeFilterChange,
  onOpenPump,
  onOpenDrawing,
  onOpenPM,
  onOpenCM,
  onOpenWorkOrder,
}) {
  const [drawer, setDrawer] = useState(null); // null | "preview"

  const meta = statusMeta(document.status);
  const current = findCurrentDocumentRevision(document);
  const revisions = document.revisions ?? [];
  const previewAvailable = isFilePreviewAvailable(document);
  const downloadAvailable = isFileDownloadAvailable(document);

  const linkedAssetItems = document.equipmentTag
    ? [{ key: document.equipmentTag, name: document.equipmentTag, flagLabel: "Linked" }]
    : [];

  return (
    <div className="ltsa-open-design" data-testid="document-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {document.equipmentTag ? (
              <button
                type="button"
                className="crumb-link"
                onClick={() => onOpenPump?.(document.equipmentTag)}
                data-od-id="crumb-pump-link"
              >
                {document.equipmentTag}
              </button>
            ) : (
              <span>Reference Library</span>
            )}
            <span className="sep">›</span><span>Document</span>
            <span className="sep">›</span><b>{document.documentNumber}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{document.title}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              <span className="running-line">
                <span className="dot-sm" />
                Rev {document.currentRevision ?? "—"}
              </span>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="Document Number" value={document.documentNumber} valueClassName="mono" />
              <InfoRow label="Document Type" value={document.documentType ?? "—"} />
              <InfoRow label="Category" value={document.category ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Discipline" value={document.discipline ?? "—"} />
              <InfoRow label="Created" value={document.createdAt ?? "—"} />
              <InfoRow label="Updated" value={document.updatedAt ?? "—"} />
            </div>
          </section>

          <Section id="document-overview-section" title="Document Overview">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <div className="eyebrow">Classification</div>
                <InfoRow label="Document Type" value={document.documentType ?? "—"} />
                <InfoRow label="Category" value={document.category ?? "—"} />
              </div>
              <div>
                <div className="eyebrow">Authorship</div>
                <InfoRow label="Author" value={current?.author ?? "Unavailable"} />
                <InfoRow label="Checker" value={current?.checker ?? "Unavailable"} />
                <InfoRow label="Approver" value={current?.approvedBy ?? "Unavailable"} />
              </div>
            </div>
          </Section>

          {/* MWO-LTSA-072 -- Source Document: real file metadata, never
              fabricated (unmapped fields default null in documentMapping.js).
              Preview/Download are real working links only when
              file_reference is a directly browser-fetchable http(s) URL --
              otherwise an honest "unavailable" disclosure, matching
              DrawingViewerPanel.jsx's own "Download (Coming soon)"
              precedent. */}
          <Section id="source-document-section" title="Source Document">
            <div style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="File Name" value={document.fileName ?? "—"} />
              <InfoRow label="File Format" value={document.fileFormat ?? "—"} />
              <InfoRow label="Page Count" value={document.pageCount ?? "—"} />
              <InfoRow label="Manufacturer" value={document.manufacturer ?? "—"} />
              <InfoRow label="Language" value={document.language ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-2)", display: "flex", gap: "var(--space-3)" }}>
              {previewAvailable ? (
                <a
                  href={document.fileReference}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-link"
                  data-od-id="source-document-preview-link"
                >
                  Preview Source Document →
                </a>
              ) : (
                <span className="confidence-label ref-group-empty" data-od-id="source-document-preview-unavailable">
                  Preview unavailable — no directly accessible file reference on record.
                </span>
              )}
              {downloadAvailable ? (
                <a
                  href={document.fileReference}
                  download
                  className="btn-link"
                  data-od-id="source-document-download-link"
                >
                  Download →
                </a>
              ) : (
                <span className="confidence-label ref-group-empty" data-od-id="source-document-download-unavailable">
                  Download unavailable — no directly accessible file reference on record.
                </span>
              )}
            </div>
          </Section>

          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Status" value={meta.label} />
              <InfoRow label="Current Revision" value={document.currentRevision ?? "Unknown"} />
              <InfoRow label="Discipline" value={document.discipline ?? "Unknown"} />
              <InfoRow label="Linked Asset" value={document.equipmentTag ?? "No linked assets"} />
            </div>
          </Section>

          <Section id="revision-history-section" title="Revision History">
            <div style={{ marginTop: "var(--space-3)" }}>
              {revisions.length > 0 ? (
                <Table rowKey="revision" data={revisions} columns={REVISION_COLUMNS} />
              ) : (
                <p className="confidence-label ref-group-empty">No revision history</p>
              )}
            </div>
          </Section>

          <Section id="linked-assets-section" title="Linked Assets">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Linked Equipment" items={linkedAssetItems} emptyReason="No linked assets" />
            </div>
          </Section>

          <Section id="reference-documents-section" title="Reference Documents">
            <div style={{ marginTop: "var(--space-3)" }}>
              <DocumentReferencePanel
                bare
                documentTypeFilter={documentTypeFilter}
                onDocumentTypeFilterChange={onDocumentTypeFilterChange}
              />
            </div>
          </Section>

          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier="unavailable" label="Unavailable" dot={false} />
              <div style={{ marginTop: "var(--space-2)" }}>
                <InfoRow label="Reason" value="Reserved for a future Engineering AI capability." />
              </div>
            </div>
          </Section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="document-status-section" title="Document Status">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="linked-asset-section" title="Linked Asset">
            <div className={document.equipmentTag ? "confidence-label" : "confidence-label ref-group-empty"}>
              {document.equipmentTag ?? "No linked assets"}
            </div>
          </RailSection>

          <RailSection id="latest-revision-section" title="Latest Revision">
            <div className="confidence-label">
              {current ? `Rev ${current.revision} · ${current.date ?? "—"}` : "No revision history"}
            </div>
          </RailSection>

          <RailSection id="recent-activities-section" title="Recent Activities">
            <div className="confidence-label ref-group-empty">No recent activity available.</div>
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${document.documentNumber} · ${meta.label}`}
        metaPrimary={document.category ?? "Unknown"}
        metaLabel="Revision"
        metaValue={document.currentRevision ?? "Unknown"}
      >
        <button type="button" className="btn-link" onClick={() => setDrawer("preview")} data-od-id="action-bar-view-document">
          View Document →
        </button>
        {document.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenPM?.(document.equipmentTag)} data-od-id="action-bar-open-pm">
            Open PM →
          </button>
        )}
        {document.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenCM?.(document.equipmentTag)} data-od-id="action-bar-open-cm">
            Open CM →
          </button>
        )}
        {document.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenWorkOrder?.(document.equipmentTag)} data-od-id="action-bar-open-workorder">
            Open Work Order →
          </button>
        )}
        {document.equipmentTag && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(document.equipmentTag)} data-od-id="action-bar-open-pump">
            Open Pump →
          </button>
        )}
        {document.equipmentTag && (
          <button
            type="button"
            className="btn-primary"
            onClick={() => onOpenDrawing?.(document.equipmentTag)}
            data-od-id="action-bar-open-drawing"
          >
            Open Drawing
          </button>
        )}
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "preview"} onClose={() => setDrawer(null)} title="Document Preview">
        <div className="drawing-thumb" />
        {previewAvailable ? (
          <p>
            <a href={document.fileReference} target="_blank" rel="noreferrer" data-od-id="document-preview-drawer-link">
              Open source document →
            </a>
          </p>
        ) : (
          <p>Static preview placeholder — no document file/rendering backend exists yet.</p>
        )}
      </PumpWorkspaceDrawer>
    </div>
  );
}
