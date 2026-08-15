import { Badge, Table } from "../../../design-system";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapSealRecord } from "../utils/sealMapping";
import { mapInstallationRecord } from "../utils/installationMapping";
import { mapDocumentRecord } from "../utils/documentMapping";
import { deriveDrawingRecords, describeRelationship } from "../utils/knowledgeReviewMapping";

/**
 * MWO-LTSA-078 -- Knowledge Review Workspace. Built entirely from the
 * shared components/open-design/ Kit (Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup, MWO-LTSA-050B) plus the design-system
 * Table/Badge -- no new design language, no new CSS, no new widget.
 *
 * Display only: no editing, no importing, no upload -- this file renders
 * an already-built Knowledge Package (the real ImportPackage entity lists
 * plus its real ValidatedImportPackage validation result,
 * CORE-SERVICES/API/import_validator.py, MWO-LTSA-076, "COMPLETE") and
 * nothing else. No fetch, no mutation, no local editable state anywhere
 * in this file.
 *
 * Reuse, not a duplicate mapping layer: Pump/Seal/Installation/Document
 * rows are mapped by the EXISTING pumpMapping.js/sealMapping.js/
 * installationMapping.js/documentMapping.js -- the exact same reuse
 * import_validator.py's own header comment names verbatim ("the four
 * entity shapes read here ... are exactly the snake_case 'Raw Backend'
 * shapes pumpMapping.js/sealMapping.js/installationMapping.js/
 * documentMapping.js already map from"). mapDocumentRecord() is called
 * with an empty compatibilityRecords array (no seal_pump_compatibility
 * data exists in a Knowledge Package) -- this is that function's own
 * already-established honest default (category -> "Reference",
 * equipmentTag -> null), not a new code path.
 *
 * Drawing is not a separate backend list -- deriveDrawingRecords()
 * (knowledgeReviewMapping.js) filters `documents` to document_type ===
 * "DRAWING", the same real relationship LTSAKnowledgeService._build_drawings()
 * already uses, so this workspace's own Drawing section never invents a
 * second data source.
 *
 * PM / Seal / Failure Analysis are NOT part of the backend's
 * ImportPackage/ValidatedImportPackage (confirmed by reading
 * import_validator.py in full before writing this file: only pumps/
 * seals/installations/documents exist) -- rather than fabricating rows
 * for entity types this Knowledge Package genuinely does not carry, PM/
 * CM/Failure render the same honest "not included in this Knowledge
 * Package" disclosure DocumentOpenDesignView's own Remarks section
 * (MWO-LTSA-068) already established for an analogous "the field this
 * MWO names doesn't exist in the real data model" situation.
 *
 * Validation: Summary/Errors/Warnings/Relationships are the real
 * ValidatedImportPackage fields, unchanged -- Errors/Warnings/
 * Relationships reuse the design-system Table (already used by Document's
 * Revision History and Drawing's BOM for exactly this "several named
 * fields per row" shape) rather than forcing them into RefGroup's
 * single-line-item shape.
 *
 * Action Bar: reuses the exact onNavigate(key, context) contract every
 * other workspace's Action Bar already uses ("Open Pump"/"Open Seal"/
 * "Open Installation" for the package's first record of each type, when
 * present) -- navigation only, never editing/importing/uploading.
 */
export default function KnowledgeReviewWorkspaceView({ knowledgePackage, onNavigate }) {
  const rawPumps = knowledgePackage.pumps ?? [];
  const rawSeals = knowledgePackage.seals ?? [];
  const rawInstallations = knowledgePackage.installations ?? [];
  const rawDocuments = knowledgePackage.documents ?? [];
  const validation = knowledgePackage.validation ?? { summary: null, errors: [], warnings: [], relationships: [] };

  const pumps = rawPumps.map(mapPumpRecord);
  const seals = rawSeals.map(mapSealRecord);
  const installations = rawInstallations.map(mapInstallationRecord);
  const documents = rawDocuments.map((record) => mapDocumentRecord(record, [], rawDocuments));
  const drawings = deriveDrawingRecords(rawDocuments).map((record) => mapDocumentRecord(record, [], rawDocuments));

  const summary = validation.summary;
  const errors = validation.errors ?? [];
  const warnings = validation.warnings ?? [];
  const relationships = validation.relationships ?? [];

  const pumpItems = pumps.map((p) => ({ key: p.tag, name: p.tag, meta: p.name, flagLabel: p.status }));
  const sealItems = seals.map((s) => ({ key: s.code, name: s.code, meta: s.name, flagLabel: s.status }));
  const installationItems = installations.map((i) => ({
    key: i.id,
    name: i.reportNo ?? i.id,
    meta: i.plantEquipNo ? `Pump ${i.plantEquipNo}` : "No linked pump",
  }));
  const documentItems = documents.map((d) => ({
    key: d.id,
    name: d.documentNumber ?? d.id,
    meta: d.title,
    flagLabel: d.documentType,
  }));
  const drawingItems = drawings.map((d) => ({
    key: d.id,
    name: d.documentNumber ?? d.id,
    meta: d.title,
    flagLabel: d.currentRevision ? `Rev ${d.currentRevision}` : null,
  }));

  const validVariant = summary?.is_valid ? "normal" : "critical";
  const validLabel = summary?.is_valid ? "Valid" : "Invalid";

  const errorRows = errors.map((item, index) => ({ ...item, _rowKey: `${item.code}-${index}` }));
  const warningRows = warnings.map((item, index) => ({ ...item, _rowKey: `${item.code}-${index}` }));
  const relationshipRows = relationships.map((item, index) => ({
    ...item,
    _rowKey: `${item.from_entity_type}-${item.from_entity_id}-${item.field}-${index}`,
    description: describeRelationship(item),
  }));

  const findingColumns = [
    { key: "code", header: "Code" },
    { key: "entity_type", header: "Entity Type" },
    { key: "entity_id", header: "Entity ID", render: (value) => value ?? "—" },
    { key: "field", header: "Field", render: (value) => value ?? "—" },
    { key: "message", header: "Message" },
  ];

  return (
    <div className="ltsa-open-design" data-testid="knowledge-review-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            <span>Knowledge Review</span>
            <span className="sep">›</span>
            <b>{summary ? `${summary.pump_count + summary.seal_count + summary.installation_count + summary.document_count} records` : "0 records"}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>Knowledge Package Review</h1>
            <div className="identity-status">
              {summary && <StatusSignal tier={validVariant} label={validLabel} />}
              <span className="running-line">
                <span className="dot-sm" />
                {summary
                  ? `${summary.error_count} errors · ${summary.warning_count} warnings`
                  : "No Knowledge Package loaded"}
              </span>
            </div>
          </section>

          <Section id="pump-section" title="Pump">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Pumps" items={pumpItems} emptyReason="No pumps in this Knowledge Package" />
            </div>
          </Section>

          <Section id="seal-section" title="Seal">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Seals" items={sealItems} emptyReason="No seals in this Knowledge Package" />
            </div>
          </Section>

          <Section id="installation-section" title="Installation">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Installations" items={installationItems} emptyReason="No installations in this Knowledge Package" />
            </div>
          </Section>

          <Section id="drawing-section" title="Drawing">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Drawings" items={drawingItems} emptyReason="No drawings in this Knowledge Package" />
            </div>
          </Section>

          <Section id="document-section" title="Document">
            <div style={{ marginTop: "var(--space-3)" }}>
              <RefGroup title="Documents" items={documentItems} emptyReason="No documents in this Knowledge Package" />
            </div>
          </Section>

          {/* PM / CM / Failure: no real data source -- the backend's own
              ImportPackage/ValidatedImportPackage does not carry these
              entity types (confirmed by reading import_validator.py in
              full). Honestly disclosed, never fabricated. */}
          <Section id="pm-section" title="PM">
            <p className="confidence-label ref-group-empty" style={{ marginTop: "var(--space-3)" }}>
              Not included in this Knowledge Package.
            </p>
          </Section>

          <Section id="cm-section" title="CM">
            <p className="confidence-label ref-group-empty" style={{ marginTop: "var(--space-3)" }}>
              Not included in this Knowledge Package.
            </p>
          </Section>

          <Section id="failure-section" title="Failure">
            <p className="confidence-label ref-group-empty" style={{ marginTop: "var(--space-3)" }}>
              Not included in this Knowledge Package.
            </p>
          </Section>

          <Section id="relationships-section" title="Relationships">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relationshipRows.length > 0 ? (
                <Table
                  rowKey="_rowKey"
                  data={relationshipRows}
                  columns={[
                    { key: "description", header: "Relationship" },
                    {
                      key: "resolved",
                      header: "Status",
                      render: (value) => (value ? <Badge variant="success">Resolved</Badge> : <Badge variant="warning">Unresolved</Badge>),
                    },
                  ]}
                />
              ) : (
                <p className="confidence-label ref-group-empty">No relationships found in this Knowledge Package</p>
              )}
            </div>
          </Section>

          <Section id="validation-section" title="Validation">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {summary ? (
                <>
                  <InfoRow label="Valid" value={summary.is_valid ? "Yes" : "No"} />
                  <InfoRow label="Pumps" value={summary.pump_count} />
                  <InfoRow label="Seals" value={summary.seal_count} />
                  <InfoRow label="Installations" value={summary.installation_count} />
                  <InfoRow label="Documents" value={summary.document_count} />
                  <InfoRow label="Errors" value={summary.error_count} />
                  <InfoRow label="Warnings" value={summary.warning_count} />
                  <InfoRow label="Relationships" value={summary.relationship_count} />
                  <InfoRow label="Unresolved Relationships" value={summary.unresolved_relationship_count} />
                </>
              ) : (
                <p className="confidence-label ref-group-empty">No validation summary available</p>
              )}
            </div>

            <div style={{ marginTop: "var(--space-3)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Errors</div>
              {errorRows.length > 0 ? (
                <Table rowKey="_rowKey" data={errorRows} columns={findingColumns} />
              ) : (
                <p className="confidence-label ref-group-empty">No errors</p>
              )}
            </div>

            <div style={{ marginTop: "var(--space-3)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Warnings</div>
              {warningRows.length > 0 ? (
                <Table rowKey="_rowKey" data={warningRows} columns={findingColumns} />
              ) : (
                <p className="confidence-label ref-group-empty">No warnings</p>
              )}
            </div>
          </Section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="validation-status-section" title="Validation Status">
            {summary ? <StatusSignal tier={validVariant} label={validLabel} /> : <div className="confidence-label ref-group-empty">No Knowledge Package loaded</div>}
          </RailSection>

          <RailSection id="counts-section" title="Counts">
            <div className="confidence-label">
              {summary
                ? `${summary.pump_count} pumps · ${summary.seal_count} seals · ${summary.installation_count} installations · ${summary.document_count} documents`
                : "No Knowledge Package loaded"}
            </div>
          </RailSection>

          <RailSection id="findings-section" title="Findings">
            <div className="confidence-label">
              {summary ? `${summary.error_count} errors · ${summary.warning_count} warnings` : "No findings"}
            </div>
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={summary ? `Knowledge Package · ${validLabel}` : "Knowledge Package · Empty"}
        metaPrimary={summary ? `${summary.error_count} errors` : "0 errors"}
        metaLabel="Warnings"
        metaValue={summary ? summary.warning_count : 0}
      >
        {pumps[0] && (
          <button type="button" className="btn-link" onClick={() => onNavigate?.("pump", { selectId: pumps[0].tag })} data-od-id="action-bar-open-pump">
            Open Pump →
          </button>
        )}
        {seals[0] && (
          <button type="button" className="btn-link" onClick={() => onNavigate?.("seal", { selectId: seals[0].code })} data-od-id="action-bar-open-seal">
            Open Seal →
          </button>
        )}
        {installations[0] && (
          <button
            type="button"
            className="btn-link"
            onClick={() => onNavigate?.("installation", { selectId: installations[0].id })}
            data-od-id="action-bar-open-installation"
          >
            Open Installation →
          </button>
        )}
      </ActionBar>
    </div>
  );
}
