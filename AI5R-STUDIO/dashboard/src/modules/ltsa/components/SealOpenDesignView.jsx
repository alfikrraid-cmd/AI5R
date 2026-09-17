import { useMemo, useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import AssetIdentityHeader, { HealthCard } from "./AssetIdentityHeader";
import WorkspaceTabStrip from "./WorkspaceTabStrip";
import { IconSeal } from "./LTSANavIcons";
import { Section, InfoRow, StatusSignal, RefGroup } from "./open-design";
import { Table } from "../../../design-system";
import {
  EngineeringAIStatus,
  EngineeringAISummary,
  EngineeringAIProviderInfo,
  EngineeringAIConfidence,
  EngineeringAIRisk,
  EngineeringAIRemainingLife,
  EngineeringAIFindings,
  EngineeringAIEvidence,
  EngineeringAIRecommendation,
  EngineeringAISourceReferences,
} from "./engineering-ai";

/**
 * MWO-LTSA-042A -- Mechanical Seal Workspace, rebuilt to match the approved
 * Open Design. ChromeBar, Identity/Hero, Compatibility/Related Engineering
 * (RefGroup-based), sticky Inspector Rail, sticky Action Bar, a Drawer
 * (reused from PumpWorkspaceDrawer.jsx), and a Toast.
 *
 * Data discipline (never fabricate): every group/field below either shows
 * real, already-fetched data or an honest empty state -- never the Open
 * Design mockup's own illustrative placeholder content.
 *
 * MWO-LTSA-044/045/046/047/048 -- UX polish + reorg passes: Contract
 * Coverage/LTSA Coverage card, lighter/shorter empty states, denser
 * Hero/rail/section rhythm, Engineering AI in a bordered .info-panel,
 * workflow-oriented section reorder (Current Status card, Hero grouped
 * into Identity/Technical, Engineering Overview promoted, Engineering
 * Recommendation collapse-when-empty, Engineering AI Reason/Required
 * Action), Engineering Context section, RefGroup emptyReason.
 *
 * MWO-LTSA-050 -- Pump Workspace migrated to the same hierarchy
 * (PumpOpenDesignView.jsx), sharing LTSAOpenDesign.css (renamed from
 * Seal.opendesign.css, .seal-open-design -> .ltsa-open-design).
 *
 * MWO-LTSA-050B -- LTSA Open Design Kit: Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup extracted to components/open-design/
 * (Priority 1 patterns only, proven identical or near-identical between
 * this file and PumpOpenDesignView.jsx -- see the archaeology report).
 * Every replacement below preserves the exact prior markup/classes/text;
 * this is a refactor, not a redesign -- no visual or behavioral change.
 * RefGroup's own local definition is gone (was byte-identical to
 * Pump's copy); the two group-array `emptyReason` derivations and all
 * seal-specific data/logic are unchanged.
 */

const NOT_AVAILABLE = "N/A";

const STATUS_META = {
  ACTIVE: { tier: "normal", label: "Sesuai Spesifikasi" },
  STANDBY: { tier: "attention", label: "Dipantau" },
  MAINTENANCE: { tier: "attention", label: "Dipantau" },
  ALERT: { tier: "high", label: "Mendekati Batas Layanan" },
  FAULT: { tier: "critical", label: "Segera Ganti" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Tidak Diketahui" };
}

// Lifecycle Stepper stage derived from the same real `status` field --
// a presentation mapping (like statusBadgeVariant/criticalityBadgeVariant
// elsewhere in this codebase), not a new fabricated data point. Seal-only
// (see PumpOpenDesignView.jsx's own header comment for why Pump has none)
// -- stays local, not part of the shared kit.
const LIFECYCLE_STEPS = [
  { id: "installed", label: "Dipasang" },
  { id: "inservice", label: "Masa Pakai Normal" },
  { id: "monitor", label: "Dipantau" },
  { id: "endoflife", label: "Akhir Masa Pakai" },
];

function lifecycleCurrentIndex(status) {
  if (status === "FAULT") return 3;
  if (status === "ALERT" || status === "STANDBY" || status === "MAINTENANCE") return 2;
  return 1;
}

export default function SealOpenDesignView({
  seal,
  stock,
  resolvedAssetCode,
  installedSince,
  pmRecords = [],
  cmRecords = [],
  conditionMonitoringReadings = [],
  workOrderRecords = [],
  documents = [],
  documentsLoading = false,
  linkedDrawings = [],
  linkedDrawingsLoading = false,
  linkedDrawingsError = null,
  drawingBomGroups = [],
  bomLoading = false,
  canEditIdentifiers = false,
  onUpdateIdentifiers,
  onOpenPump,
  onOpenDrawing,
  onBack,
  aiResponse,
  aiReady,
  aiStatusText,
  aiStatusVariant,
  aiStatusLabel,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing" | "recommendation"
  const [toast, setToast] = useState(null);
  const [reviewed, setReviewed] = useState(false);
  // UI-D1.2 -- Overview/Compatible/Documents/History/AI Insight, matching
  // Chief's reference tab list for the Mechanical Seal Workspace. Purely a
  // display grouping over sections that already existed -- see each tab's
  // own comment below for exactly which pre-existing section moved where.
  //
  // R2B -- Drawings/BOM added, explicitly authorized (Chief Architect's
  // own canonical chain: Seal -> Engineering Drawing SEAL link -> Drawing
  // Revision -> BOM Lines). Kept distinct from Documents (R2A,
  // seal_engineering_document -- a different table/domain, untouched by
  // this addition) per that same instruction.
  const [activeTab, setActiveTab] = useState("overview");
  const SEAL_TABS = [
    { key: "overview", label: "Overview" },
    { key: "compatible", label: "Compatible" },
    { key: "documents", label: "Documents" },
    { key: "drawings", label: "Drawings" },
    { key: "bom", label: "BOM" },
    { key: "history", label: "History" },
    { key: "ai-insight", label: "AI Insight" },
  ];

  // MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- KIMAP Pertamina / GPN John
  // Crane manual completion. View mode always renders (every role with
  // seal.read, including JOHN_CRANE_ENGINEER and both Pertamina roles);
  // the edit form only ever renders when canEditIdentifiers is true
  // (Seal.jsx derives this from master.edit) -- the backend PATCH route
  // remains the real enforcement point regardless (same "prop hides UI,
  // backend decides" discipline AdminUsersView.jsx already established).
  const [editingIdentifiers, setEditingIdentifiers] = useState(false);
  const [identifierForm, setIdentifierForm] = useState({ kimapPertamina: "", gpnJohnCrane: "" });
  const [identifierError, setIdentifierError] = useState(null);
  const [savingIdentifiers, setSavingIdentifiers] = useState(false);

  function startEditingIdentifiers() {
    setIdentifierForm({
      kimapPertamina: seal.kimapPertamina ?? "",
      gpnJohnCrane: seal.gpnJohnCrane ?? "",
    });
    setIdentifierError(null);
    setEditingIdentifiers(true);
  }

  async function handleSaveIdentifiers(event) {
    event.preventDefault();
    setIdentifierError(null);
    setSavingIdentifiers(true);
    try {
      await onUpdateIdentifiers?.(seal.code, identifierForm);
      setEditingIdentifiers(false);
    } catch (err) {
      // Verbatim backend detail (e.g. a 403 if permissions changed
      // mid-session, or a 404 if the seal was removed) -- never a
      // generic "failed" message, same discipline as AdminUsersView.jsx.
      setIdentifierError(err.message);
    } finally {
      setSavingIdentifiers(false);
    }
  }

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(null), 2600);
  }

  // R2A -- real seal_engineering_document rows (documents prop, mapped by
  // Seal.jsx via documentMapping.js's mapDocumentRecord, exact-match on
  // seal_code). Grouped by the raw document_type enum verbatim (DRAWING/
  // DATASHEET/INSTALLATION_GUIDE/INSPECTION_SHEET/MAINTENANCE_MANUAL/
  // SERVICE_BULLETIN/ENGINEERING_SPECIFICATION) -- never translated into
  // the old placeholder's Drawing/Datasheet/Installation Procedure/
  // Certificates/Revision History labels, since no real, evidenced
  // mapping between the two vocabularies exists (documentMapping.js's own
  // disclosed-gap discipline; inventing one here would be fabricated
  // metadata). Only groups with at least one real document are rendered.
  const documentGroups = useMemo(() => {
    const byType = new Map();
    for (const doc of documents) {
      const type = doc.documentType ?? "UNSPECIFIED";
      if (!byType.has(type)) byType.set(type, []);
      byType.get(type).push({
        key: doc.id,
        name: doc.title || doc.documentNumber || doc.id,
        meta: doc.documentNumber ? `No. ${doc.documentNumber}` : undefined,
        flagLabel: doc.currentRevision ? `Rev ${doc.currentRevision}` : undefined,
      });
    }
    return [...byType.entries()].map(([type, items]) => ({ type, items }));
  }, [documents]);

  const meta = statusMeta(seal.status);

  const coverageMeta = resolvedAssetCode
    ? { tier: "normal", label: "LTSA Covered", message: "Linked to an LTSA-covered pump." }
    : { tier: "neutral", label: "Outside LTSA Contract", message: "Outside active LTSA scope." };

  const requiredAction =
    !resolvedAssetCode && aiStatusVariant === "unavailable"
      ? "Associate this seal with an LTSA-covered asset."
      : null;

  const ltsaEmptyReason = "No LTSA association";
  const dataEmptyReason = "No engineering data";

  const compatibilityGroups = [
    {
      id: "pumps",
      title: "Compatible Pumps",
      items: seal.compatiblePumps.map((tag) => ({ key: tag, name: tag, flagLabel: "Kompatibel" })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    { id: "plans", title: "Compatible API Plans", items: [], emptyReason: dataEmptyReason },
    { id: "services", title: "Compatible Services", items: [], emptyReason: dataEmptyReason },
    {
      id: "materials",
      title: "Compatible Materials",
      items: seal.material ? [{ key: "material", name: seal.material, flagLabel: "Terdaftar" }] : [],
      emptyReason: dataEmptyReason,
    },
    {
      id: "replacements",
      title: "Compatible Replacements",
      items: seal.compatibleSeals.map((code) => ({ key: code, name: code, flagLabel: "Kompatibel" })),
      emptyReason: dataEmptyReason,
    },
  ];

  const relatedGroups = [
    {
      id: "pm",
      title: "Related PM",
      items: pmRecords.map((pm) => ({ key: pm.id, name: pm.id, meta: pm.nextDue ? `Jatuh tempo ${pm.nextDue}` : pm.procedure, flagLabel: pm.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    {
      id: "cm",
      title: "Related Condition Monitoring",
      // MWO-R2C3 -- genuine condition_monitoring_reading rows (never
      // Corrective Maintenance -- see "Related CM Reports" below, a
      // separate legacy group left untouched). Seal Master -> compatible
      // pump -> CM reading only; no physical-seal-unit claim.
      items: conditionMonitoringReadings.map((cm) => ({
        key: cm.id,
        name: cm.id,
        meta: [
          cm.readingDate ? `Reading ${cm.readingDate}` : "Reading date N/A",
          `DE leak: ${cm.leakDe === true ? "Yes" : cm.leakDe === false ? "No" : "N/A"}`,
          `NDE leak: ${cm.leakNde === true ? "Yes" : cm.leakNde === false ? "No" : "N/A"}`,
        ].join(" · "),
        flagLabel: cm.status ?? "N/A",
      })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    { id: "fa", title: "Related Failure Analysis", items: [], emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason },
    {
      id: "cm-reports",
      title: "Related CM Reports",
      items: cmRecords.map((cm) => ({ key: cm.id, name: cm.id, meta: cm.failureDescription, flagLabel: cm.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    {
      id: "wo",
      title: "Related Work Orders",
      items: workOrderRecords.map((wo) => ({ key: wo.id, name: wo.id, meta: wo.title, flagLabel: wo.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
  ];

  const preferredReplacement = seal.compatibleSeals[0]
    ? { name: seal.compatibleSeals[0], meta: "Interchange tercatat pada Seal Registry" }
    : null;

  return (
    <div className="ltsa-open-design" data-testid="seal-open-design">
      <AssetIdentityHeader
        icon={<IconSeal />}
        tag={seal.code}
        name={seal.name}
        subtitle={
          resolvedAssetCode
            ? (installedSince ? `Installed on ${resolvedAssetCode} since ${installedSince}` : `Installed on ${resolvedAssetCode}`)
            : "Outside LTSA scope"
        }
        onBack={onBack}
      >
        <HealthCard label="Status" value={meta.label} tone={meta.tier} />
        <HealthCard label="Stock" value={stock ? (stock.quantityOnHand ?? "Unknown") : "Unknown"} />
      </AssetIdentityHeader>

      <WorkspaceTabStrip items={SEAL_TABS} activeKey={activeTab} onChange={setActiveTab} />

      {activeTab === "overview" && (
        <div className="workspace-overview-grid">
          <div className="workspace-overview-card">
            <div className="eyebrow">Seal Overview</div>
            <InfoRow label="Seal Family" value={seal.type ?? "—"} />
            <InfoRow label="Pressure Max" value={seal.pressureLimit != null ? `${seal.pressureLimit} bar` : NOT_AVAILABLE} />
            <InfoRow label="Temperature" value={seal.temperatureLimit != null ? `${seal.temperatureLimit}°C` : NOT_AVAILABLE} />
            {/* UI-D1.2 -- Chief's reference names Installed Date/MTBF/
                Operating Hours as example real fields for this card. No
                field for any of the three exists anywhere in this
                codebase's seal data model (sealMapping.js/seal registry
                schema confirmed during this MWO's own audit) -- shown
                honestly as N/A, never fabricated. */}
            <InfoRow label="Installed Date" value={NOT_AVAILABLE} />
            <InfoRow label="MTBF" value={NOT_AVAILABLE} />
            <InfoRow label="Operating Hours" value={NOT_AVAILABLE} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Construction</div>
            <InfoRow label="Material" value={seal.material ?? "—"} />
            <InfoRow label="Shaft Size" value={seal.shaftSize != null ? `${seal.shaftSize} mm` : "—"} />
            {/* Faces/Elastomer/Spring/Balanced/Rotation -- reference's
                example construction fields; no field for any exists in
                this seal data model (only Material/Shaft do). N/A, not
                fabricated. */}
            <InfoRow label="Faces" value={NOT_AVAILABLE} />
            <InfoRow label="Elastomer" value={NOT_AVAILABLE} />
            <InfoRow label="Spring" value={NOT_AVAILABLE} />
            <InfoRow label="Balanced" value={NOT_AVAILABLE} />
            <InfoRow label="Rotation" value={NOT_AVAILABLE} />
          </div>

          <div className="workspace-overview-card">
            <div className="eyebrow">Status</div>
            <InfoRow label="Health" value={meta.label} />
            <InfoRow label="Coverage" value={coverageMeta.label} />
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
            {!resolvedAssetCode && (
              <>
                <div className="confidence-label" style={{ fontWeight: 600, marginTop: "var(--space-2)", marginBottom: "var(--space-1)" }}>Unavailable</div>
                <ul style={{ margin: 0, paddingLeft: "var(--space-4)" }}>
                  <li className="confidence-label">PM History</li>
                  <li className="confidence-label">Engineering AI</li>
                  <li className="confidence-label">Asset Analytics</li>
                </ul>
              </>
            )}
            {/* Risk Level/Confidence -- reference's example status fields;
                no risk-scoring/confidence model exists for seals in this
                codebase. N/A, not fabricated. */}
            <InfoRow label="Risk Level" value={NOT_AVAILABLE} />
            <InfoRow label="Confidence" value={NOT_AVAILABLE} />
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Identity &amp; Identifiers</div>
            <div className="assessment-columns" style={{ marginTop: "var(--space-2)" }}>
              <div>
                <InfoRow label="Code" value={seal.code} valueClassName="mono" />
                <InfoRow label="Manufacturer" value={seal.manufacturer ?? "—"} />
                <InfoRow label="Model" value={seal.model ?? "—"} />
              </div>
              <div data-od-id="seal-identifiers-section">
                {!editingIdentifiers ? (
                  <>
                    <InfoRow
                      label="KIMAP Pertamina"
                      value={seal.kimapPertamina ?? "Not yet completed"}
                      valueClassName={seal.kimapPertamina ? undefined : "ref-group-empty"}
                    />
                    <InfoRow
                      label="GPN John Crane"
                      value={seal.gpnJohnCrane ?? "Not yet completed"}
                      valueClassName={seal.gpnJohnCrane ? undefined : "ref-group-empty"}
                    />
                    <InfoRow
                      label="Last Updated"
                      value={seal.updatedAt ? String(seal.updatedAt).slice(0, 19).replace("T", " ") : "—"}
                    />
                    <InfoRow
                      label="Updated By (User ID)"
                      value={seal.updatedBy ?? "Imported / system data"}
                    />
                    {canEditIdentifiers && (
                      <button
                        type="button"
                        className="btn-link"
                        onClick={startEditingIdentifiers}
                        data-od-id="edit-identifiers-btn"
                      >
                        Edit KIMAP / GPN →
                      </button>
                    )}
                  </>
                ) : (
                  <form onSubmit={handleSaveIdentifiers} data-testid="seal-identifiers-form">
                    {identifierError && (
                      <p
                        className="confidence-label"
                        style={{ color: "var(--color-danger, #d33)" }}
                        data-testid="seal-identifiers-error"
                      >
                        {identifierError}
                      </p>
                    )}
                    <label htmlFor={`kimap-${seal.code}`} className="confidence-label">KIMAP Pertamina</label>
                    <input
                      id={`kimap-${seal.code}`}
                      value={identifierForm.kimapPertamina}
                      onChange={(e) => setIdentifierForm((f) => ({ ...f, kimapPertamina: e.target.value }))}
                    />
                    <label htmlFor={`gpn-${seal.code}`} className="confidence-label">GPN John Crane</label>
                    <input
                      id={`gpn-${seal.code}`}
                      value={identifierForm.gpnJohnCrane}
                      onChange={(e) => setIdentifierForm((f) => ({ ...f, gpnJohnCrane: e.target.value }))}
                    />
                    <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                      <button type="submit" className="btn-primary" disabled={savingIdentifiers}>
                        {savingIdentifiers ? "Saving…" : "Save"}
                      </button>
                      <button type="button" className="btn-link" onClick={() => setEditingIdentifiers(false)}>
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>

          <div className="workspace-overview-card" style={{ gridColumn: "1 / -1" }}>
            <div className="eyebrow">Stock Status</div>
            {stock ? (
              <>
                <InfoRow label="Quantity On Hand" value={stock.quantityOnHand ?? "Unknown"} />
                <InfoRow label="Reorder Point" value={stock.reorderPoint ?? "—"} />
                <InfoRow label="Location" value={stock.location ?? "—"} />
              </>
            ) : (
              <InfoRow label="Inventory Status" value="Unknown" valueClassName="ref-group-empty" />
            )}
          </div>
        </div>
      )}

      {activeTab === "compatible" && (
        <div className="workspace-tab-body">
          <Section id="compatibility-section" title="Compatibility">
            <div style={{ marginTop: "var(--space-3)" }}>
              {compatibilityGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>
        </div>
      )}

      {activeTab === "documents" && (
        <div className="workspace-tab-body">
          {/* Documents deliberately keeps raw markup -- its eyebrow sits
              inside .section-head alongside a button, deviating from the
              generic Section shape (see the archaeology report). */}
          <section className="assessment-section" data-od-id="documents-section">
            <div className="section-head">
              <span className="eyebrow">Documents</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => { onOpenDrawing?.(); setDrawer("drawing"); }}
                data-od-id="open-drawing-link"
              >
                Buka Drawing →
              </button>
            </div>
            <div style={{ marginTop: "var(--space-2)" }} data-od-id="documents-list">
              {documentsLoading ? (
                <p className="confidence-label" data-testid="seal-documents-loading">
                  Loading documents…
                </p>
              ) : documentGroups.length === 0 ? (
                <p className="confidence-label ref-group-empty" data-testid="seal-documents-empty">
                  No linked engineering documents for this seal.
                </p>
              ) : (
                documentGroups.map((group) => (
                  <RefGroup key={group.type} title={group.type} items={group.items} />
                ))
              )}
            </div>
          </section>
        </div>
      )}

      {activeTab === "drawings" && (
        <div className="workspace-tab-body">
          <section className="assessment-section" data-od-id="drawings-section">
            <div className="section-head">
              <span className="eyebrow">Engineering Drawings</span>
            </div>
            <div style={{ marginTop: "var(--space-2)" }} data-od-id="drawings-list">
              {linkedDrawingsLoading ? (
                <p className="confidence-label" data-testid="seal-drawings-loading">
                  Loading engineering drawings…
                </p>
              ) : linkedDrawingsError ? (
                <p className="confidence-label" role="alert" data-testid="seal-drawings-error">
                  {linkedDrawingsError}
                </p>
              ) : linkedDrawings.length === 0 ? (
                <p className="confidence-label ref-group-empty" data-testid="seal-drawings-empty">
                  No linked engineering drawings.
                </p>
              ) : (
                <RefGroup
                  title="Linked Drawings"
                  items={linkedDrawings.map((drawing) => ({
                    key: drawing.drawing_code,
                    name: drawing.title || drawing.drawing_number || drawing.drawing_code,
                    meta: drawing.drawing_number ? `No. ${drawing.drawing_number}` : undefined,
                    flagLabel: drawing.current_revision_code ? `Rev ${drawing.current_revision_code}` : undefined,
                  }))}
                />
              )}
            </div>
          </section>
        </div>
      )}

      {activeTab === "bom" && (
        <div className="workspace-tab-body">
          <section className="assessment-section" data-od-id="bom-section">
            <div className="section-head">
              <span className="eyebrow">BOM</span>
            </div>
            <div style={{ marginTop: "var(--space-2)" }} data-od-id="bom-list">
              {linkedDrawingsLoading || bomLoading ? (
                <p className="confidence-label" data-testid="seal-bom-loading">
                  Loading BOM…
                </p>
              ) : linkedDrawingsError ? (
                <p className="confidence-label" role="alert" data-testid="seal-bom-error">
                  {linkedDrawingsError}
                </p>
              ) : linkedDrawings.length === 0 ? (
                <p className="confidence-label ref-group-empty" data-testid="seal-bom-empty-no-drawing">
                  No linked engineering drawings.
                </p>
              ) : (
                // BOM_SCOPE=DRAWING_REVISION (Chief Architect's own
                // canonical chain) -- one block per linked drawing's
                // CURRENT revision, never flattened into one master-seal
                // list. A drawing with no current revision, or a
                // revision with zero BOM lines, is its own distinct
                // empty state -- never silently merged with "no linked
                // drawings" above.
                drawingBomGroups.map(({ drawing, revision, bomLines }) => (
                  <div key={drawing.drawing_code} className="assessment-section" style={{ marginBottom: "var(--space-4)" }} data-od-id="bom-drawing-group">
                    <div className="eyebrow">{drawing.title || drawing.drawing_number || drawing.drawing_code}</div>
                    {!revision ? (
                      <p className="confidence-label ref-group-empty" data-testid="seal-bom-no-current-revision">
                        No current revision set for this drawing.
                      </p>
                    ) : (
                      <>
                        <p className="confidence-label" style={{ marginBottom: "var(--space-2)" }}>
                          Revision {revision.revision ?? revision.revision_code}
                        </p>
                        {bomLines.length === 0 ? (
                          <p className="confidence-label ref-group-empty" data-testid="seal-bom-empty-no-lines">
                            No BOM recorded for this revision.
                          </p>
                        ) : (
                          <Table
                            rowKey="bom_line_code"
                            // design-system's Table renders item[column.key]
                            // verbatim -- it has no render-callback support
                            // (confirmed by reading Table.jsx; several other
                            // callers in this codebase pass an unused
                            // `render` prop that Table silently ignores, a
                            // pre-existing gap this MWO does not fix
                            // elsewhere). Pre-shaping display-ready fields
                            // here, rather than relying on a `render` prop
                            // that would not actually run, so every cell
                            // shows what it claims to.
                            data={bomLines.map((line) => ({
                              bom_line_code: line.bom_line_code,
                              item_position: line.item_position || "—",
                              component: line.component_description || line.component_id || "—",
                              // internal_component_master.gpn_number is
                              // never returned by this read path (BOM
                              // lines carry component_id only) -- honestly
                              // N/A, never inferred/guessed from
                              // component_id or seal type.
                              part_number: NOT_AVAILABLE,
                              quantity: line.quantity ?? "—",
                              material: line.material_or_specification || "—",
                            }))}
                            columns={[
                              { key: "item_position", header: "Position" },
                              { key: "component", header: "Component" },
                              { key: "part_number", header: "Part Number" },
                              { key: "quantity", header: "Qty" },
                              { key: "material", header: "Material" },
                            ]}
                          />
                        )}
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}

      {activeTab === "history" && (
        <div className="workspace-tab-body">
          <Section id="related-engineering-section" title="Related Engineering">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relatedGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          <Section id="lifecycle-section" title="Lifecycle">
            <div className="stepper" data-od-id="lifecycle-stepper" style={{ marginTop: "var(--space-3)" }}>
              {LIFECYCLE_STEPS.map((step, i) => {
                const currentIndex = lifecycleCurrentIndex(seal.status);
                const state = i < currentIndex ? "done" : i === currentIndex ? "current" : "upcoming";
                return (
                  <div className="step-item" key={step.id} data-state={state}>
                    <span className="step-dot" />
                    <div className="step-label">{step.label}</div>
                  </div>
                );
              })}
            </div>
          </Section>
        </div>
      )}

      {activeTab === "ai-insight" && (
        <div className="workspace-tab-body">
          <Section id="recommended-replacement-section" title="Engineering Recommendation">
            {seal.recommendation ? (
              <>
                <h2 className="assessment-headline">{seal.recommendation}</h2>
                {preferredReplacement && (
                  <RefGroup title="Preferred Seal" items={[{ ...preferredReplacement, flag: "ok", flagLabel: "Direkomendasikan" }]} />
                )}
                <div className="assessment-footer">
                  <StatusSignal tier={meta.tier} label={meta.label} />
                  <button type="button" className="btn-link" onClick={() => setDrawer("recommendation")} data-od-id="cta-generate-recommendation">
                    Lihat detail rekomendasi →
                  </button>
                </div>
              </>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </Section>

          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {aiReady ? (
                <>
                  <EngineeringAIStatus response={aiResponse} />
                  <EngineeringAISummary response={aiResponse} />
                  <EngineeringAIProviderInfo response={aiResponse} />
                  <EngineeringAIConfidence response={aiResponse} />
                  <EngineeringAIRisk response={aiResponse} />
                  <EngineeringAIRemainingLife response={aiResponse} />
                </>
              ) : (
                <>
                  <StatusSignal tier={aiStatusVariant} label={aiStatusLabel} dot={false} />
                  <div style={{ marginTop: "var(--space-2)" }}>
                    <InfoRow label="Reason" value={!resolvedAssetCode ? coverageMeta.label : aiStatusText} />
                    {requiredAction && <InfoRow label="Required Action" value={requiredAction} />}
                  </div>
                </>
              )}
            </div>
          </Section>
          {aiReady && <EngineeringAIFindings response={aiResponse} />}
          {aiReady && <EngineeringAIEvidence response={aiResponse} />}
          {aiReady && <EngineeringAIRecommendation response={aiResponse} />}
          {aiReady && <EngineeringAISourceReferences response={aiResponse} />}
        </div>
      )}

      {resolvedAssetCode && (
        <div className="workspace-tab-body" style={{ paddingTop: 0 }}>
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(resolvedAssetCode)} data-od-id="action-bar-open-pump">
            Buka Pump →
          </button>
        </div>
      )}

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Seal Drawing">
        <div className="drawing-thumb" />
        <p>Belum ada data drawing — Drawing Workspace belum memiliki backend.</p>
      </PumpWorkspaceDrawer>

      <PumpWorkspaceDrawer open={drawer === "recommendation"} onClose={() => setDrawer(null)} title="Generate Recommendation">
        <p>{seal.recommendation || "Belum ada rekomendasi engineering."}</p>
        {preferredReplacement && (
          <RefGroup title="Preferred Seal" items={[{ ...preferredReplacement, flag: "ok", flagLabel: "Direkomendasikan" }]} />
        )}
        {reviewed ? (
          <p style={{ color: "var(--status-normal)" }}>Rekomendasi ditandai sudah ditinjau.</p>
        ) : (
          <button
            type="button"
            className="btn-primary"
            style={{ marginTop: "var(--space-2)" }}
            onClick={() => { setReviewed(true); showToast("Rekomendasi ditandai sudah ditinjau"); }}
            data-od-id="mark-reviewed-btn"
          >
            Tandai Sudah Ditinjau
          </button>
        )}
      </PumpWorkspaceDrawer>

      <div className="toast" data-open={!!toast} data-od-id="toast">
        {toast}
      </div>
    </div>
  );
}
