import { useState } from "react";
import { Badge, Table } from "../../../design-system";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar } from "./open-design";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import KnowledgeReviewWorkspaceView from "./KnowledgeReviewWorkspaceView";

/**
 * MWO-LTSA-087/104 -- Production Import Workspace. Built entirely from the
 * shared components/open-design/ Kit (Section/InfoRow/StatusSignal/
 * RailSection/ActionBar, MWO-LTSA-050B) plus the design-system Table/Badge
 * and PumpWorkspaceDrawer -- no new design language, no new CSS, no new
 * table component, no new drawer mechanism, no new progress-bar widget.
 *
 * "No duplicate review page": the Knowledge Package (Pump/Seal/
 * Installation/Drawing/Document, plus Validation Errors/Warnings/
 * Relationships) is never re-rendered here -- KnowledgeReviewWorkspaceView
 * (MWO-LTSA-078, unmodified) is reused verbatim inside an on-demand Drawer.
 * This page's own inline "Validation Summary" section is deliberately
 * InfoRow-only (counts, no row-by-row Errors/Warnings table) so it never
 * duplicates the Table KnowledgeReviewWorkspaceView already renders for
 * that same data.
 *
 * MWO-LTSA-104 -- Conflicts are read from `session.data.conflict_report`
 * now, not a separate `conflicts` prop: POST /api/ltsa/import/session
 * computes and stores its own ConflictReport server-side (MWO-LTSA-103A),
 * so the session response IS the one, single source of truth for conflict
 * data -- no second, independently-fetched copy that could disagree with
 * it ("no duplicate state machine", this mission's own rule).
 *
 * "Progress" (this mission's own requirement) is a pure, static,
 * presentational ordinal lookup into the SAME closed status vocabulary
 * IMPORT_SESSION_STATUSES already establishes server-side
 * (import_session.py) -- exactly as much "logic" as the pre-existing
 * SESSION_STATUS_TIER lookup two lines below already has (label/tier
 * only, no transitions, no branching business rule, no new state). It is
 * not a second copy of API.import_progress.py's own richer per-step
 * derivation (never exposed via any endpoint, and this mission forbids
 * both a new API and a duplicate state machine) -- just the session's own
 * already-fetched `status` field, shown at-a-glance.
 *
 * Data discipline: every field shown is read directly off already-fetched
 * API responses (validation/session/executionResult props) -- this
 * component performs no fetch, no re-validation, no conflict
 * re-computation, no execution re-planning. All four Import API calls
 * happen in ImportWorkspace.jsx (the page); this file is render-only,
 * matching InstallationOpenDesignView.jsx/DocumentOpenDesignView.jsx's own
 * "view receives already-fetched data as props" convention.
 */

const SESSION_STATUS_TIER = {
  NEW: "neutral",
  VALIDATED: "normal",
  REVIEWING: "attention",
  APPROVED: "normal",
  EXECUTING: "attention",
  IMPORTED: "normal",
  FAILED: "critical",
};

// Same order IMPORT_SESSION_STATUSES (import_session.py) already
// establishes -- FAILED is a terminal, any-point outcome, not a forward
// stage, so it is excluded from the "Step N of 6" count (same convention
// import_progress.py's own _PIPELINE_STATES already uses server-side).
const FORWARD_SESSION_STAGES = ["NEW", "VALIDATED", "REVIEWING", "APPROVED", "EXECUTING", "IMPORTED"];

function statusTier(status) {
  return SESSION_STATUS_TIER[status] ?? "neutral";
}

function progressLabel(status) {
  if (!status) return null;
  if (status === "FAILED") return "FAILED";
  const index = FORWARD_SESSION_STAGES.indexOf(status);
  if (index === -1) return status;
  return `Step ${index + 1} of ${FORWARD_SESSION_STAGES.length}: ${status}`;
}

function packageCounts(pkg) {
  return {
    pumps: pkg?.pumps?.length ?? 0,
    seals: pkg?.seals?.length ?? 0,
    installations: pkg?.installations?.length ?? 0,
    documents: pkg?.documents?.length ?? 0,
  };
}

export default function ImportOpenDesignView({
  incomingPackage,
  incomingFileName,
  onIncomingFileSelected,
  databaseSnapshotFileName,
  onDatabaseSnapshotFileSelected,
  validation,
  session,
  executionResult,
  loadingAction,
  error,
  onValidate,
  onReview,
  onExecute,
  onRefresh,
  onNavigate,
}) {
  const [drawer, setDrawer] = useState(null); // null | "knowledge-package"

  const counts = packageCounts(incomingPackage);
  const hasIncomingPackage = counts.pumps + counts.seals + counts.installations + counts.documents > 0;

  const summary = validation?.data?.summary ?? null;
  const sessionData = session?.data ?? null;
  const conflictData = sessionData?.conflict_report ?? null;
  const stats = sessionData?.statistics ?? null;

  const conflictRows = (conflictData?.conflicts ?? []).map((item, index) => ({
    ...item,
    _rowKey: `${item.entity_type}-${item.entity_id}-${item.field}-${index}`,
  }));

  const planRows = (sessionData?.execution_plan ?? []).map((item, index) => ({
    ...item,
    _rowKey: `${item.entity_type}-${item.entity_id}-${index}`,
  }));

  const executionLogRows = (executionResult?.data?.execution_log ?? []).map((item, index) => ({
    ...item,
    _rowKey: `${item.entity_type}-${item.entity_id}-${index}`,
  }));

  const firstPump = incomingPackage?.pumps?.[0];
  const firstSeal = incomingPackage?.seals?.[0];
  const firstInstallation = incomingPackage?.installations?.[0];
  const firstDocument = incomingPackage?.documents?.[0];

  const knowledgePackageForDrawer = {
    pumps: incomingPackage?.pumps ?? [],
    seals: incomingPackage?.seals ?? [],
    installations: incomingPackage?.installations ?? [],
    documents: incomingPackage?.documents ?? [],
    validation: validation?.data ?? null,
  };

  const executing = loadingAction === "execute";

  return (
    <div className="ltsa-open-design" data-testid="import-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            <span>Import</span>
            <span className="sep">›</span>
            <b>{sessionData?.session_id ?? "No session"}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>Production Import Workspace</h1>
            <div className="identity-status">
              <StatusSignal tier={statusTier(sessionData?.status)} label={sessionData?.status ?? "No Session"} />
              <span className="running-line">
                <span className="dot-sm" />
                {hasIncomingPackage
                  ? `${counts.pumps} pumps · ${counts.seals} seals · ${counts.installations} installations · ${counts.documents} documents`
                  : "No package uploaded"}
              </span>
            </div>
            {error && (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)", color: "var(--color-danger, #c0392b)" }}>
                {error}
              </p>
            )}
          </section>

          <Section id="upload-section" title="Upload">
            <div style={{ marginTop: "var(--space-3)" }}>
              <div className="info-row">
                <span className="k">Incoming Package (required)</span>
                <span className="v">
                  <input
                    type="file"
                    accept="application/json"
                    aria-label="Upload incoming import package"
                    onChange={(event) => onIncomingFileSelected?.(event.target.files?.[0] ?? null)}
                  />
                  {incomingFileName && <span style={{ marginLeft: "var(--space-2)" }}>{incomingFileName}</span>}
                </span>
              </div>
              <div className="info-row">
                <span className="k">Database Snapshot (optional, for conflict comparison)</span>
                <span className="v">
                  <input
                    type="file"
                    accept="application/json"
                    aria-label="Upload database snapshot"
                    onChange={(event) => onDatabaseSnapshotFileSelected?.(event.target.files?.[0] ?? null)}
                  />
                  {databaseSnapshotFileName && <span style={{ marginLeft: "var(--space-2)" }}>{databaseSnapshotFileName}</span>}
                </span>
              </div>
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
                {databaseSnapshotFileName
                  ? "Conflicts will be compared against the uploaded database snapshot."
                  : "No database snapshot uploaded -- conflicts will compare against an empty snapshot (every incoming record resolves as CREATE_NEW)."}
              </p>
            </div>
          </Section>

          <Section id="validation-summary-section" title="Validation Summary">
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
                </>
              ) : (
                <p className="confidence-label ref-group-empty">Not yet validated -- click Validate in the Action Bar.</p>
              )}
            </div>
          </Section>

          <Section id="knowledge-package-section" title="Knowledge Package">
            <div className="section-head">
              <span className="eyebrow" style={{ display: "none" }} />
              <button
                type="button"
                className="btn-link"
                onClick={() => setDrawer("knowledge-package")}
                data-od-id="open-knowledge-package-link"
                disabled={!hasIncomingPackage}
              >
                View Knowledge Package →
              </button>
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>
              {hasIncomingPackage
                ? `${counts.pumps} pumps · ${counts.seals} seals · ${counts.installations} installations · ${counts.documents} documents`
                : "No Knowledge Package uploaded yet."}
            </p>
          </Section>

          <Section id="conflicts-section" title="Conflicts">
            <div style={{ marginTop: "var(--space-3)" }}>
              {conflictData ? (
                <>
                  <InfoRow label="Total Conflicts" value={conflictData.conflict_count} />
                  <InfoRow label="Manual Review" value={conflictData.manual_review_count} />
                  <InfoRow label="New Entities" value={conflictData.create_new_count} />
                  {conflictRows.length > 0 ? (
                    <div style={{ marginTop: "var(--space-2)" }}>
                      <Table
                        rowKey="_rowKey"
                        data={conflictRows}
                        columns={[
                          { key: "entity_type", header: "Entity Type" },
                          { key: "entity_id", header: "Entity ID" },
                          { key: "field", header: "Field" },
                          { key: "database_value", header: "Database Value", render: (v) => (v === null || v === undefined ? "—" : String(v)) },
                          { key: "incoming_value", header: "Incoming Value", render: (v) => (v === null || v === undefined ? "—" : String(v)) },
                          {
                            key: "resolution",
                            header: "Resolution",
                            render: (value) => <Badge variant={value === "MANUAL_REVIEW" ? "danger" : value === "CREATE_NEW" ? "info" : "success"}>{value}</Badge>,
                          },
                          {
                            key: "severity",
                            header: "Severity",
                            render: (value) => <Badge variant={value === "HIGH" ? "danger" : value === "LOW" ? "warning" : "purple"}>{value}</Badge>,
                          },
                          { key: "status", header: "Status" },
                        ]}
                      />
                    </div>
                  ) : (
                    <p className="confidence-label ref-group-empty">No conflicts found.</p>
                  )}
                </>
              ) : (
                <p className="confidence-label ref-group-empty">No conflict check has been run yet -- click Review in the Action Bar.</p>
              )}
            </div>
          </Section>

          <Section id="execution-plan-section" title="Execution Plan">
            <div style={{ marginTop: "var(--space-3)" }}>
              {planRows.length > 0 ? (
                <Table
                  rowKey="_rowKey"
                  data={planRows}
                  columns={[
                    { key: "entity_type", header: "Entity Type" },
                    { key: "entity_id", header: "Entity ID" },
                    {
                      key: "action",
                      header: "Planned Action",
                      render: (value) => <Badge variant={value === "INSERTED" ? "info" : value === "UPDATED" ? "warning" : "purple"}>{value}</Badge>,
                    },
                    { key: "table", header: "Table" },
                  ]}
                />
              ) : (
                <p className="confidence-label ref-group-empty">
                  {sessionData ? "No writes planned (nothing to insert or update)." : "No session yet -- the execution plan appears once a session has a conflict report."}
                </p>
              )}
            </div>
          </Section>

          <Section id="execution-result-section" title="Execution Result">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {executionResult ? (
                <>
                  <InfoRow label="Success" value={executionResult.success ? "Yes" : "No"} />
                  <InfoRow label="Message" value={executionResult.message ?? "—"} />
                  {executionResult.data?.status && <InfoRow label="Status" value={executionResult.data.status} />}
                  {executionResult.data?.reason && <InfoRow label="Reason" value={executionResult.data.reason} />}
                </>
              ) : (
                <p className="confidence-label ref-group-empty">Not yet executed -- click Execute in the Action Bar.</p>
              )}
            </div>
            {executionResult?.data?.statistics && (
              <div style={{ marginTop: "var(--space-3)" }}>
                <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Statistics</div>
                <Table
                  rowKey="entity"
                  data={["pump", "seal", "installation", "document"].map((entity) => ({
                    entity,
                    ...executionResult.data.statistics[entity],
                  }))}
                  columns={[
                    { key: "entity", header: "Entity Type" },
                    { key: "inserted", header: "Inserted" },
                    { key: "updated", header: "Updated" },
                    { key: "skipped", header: "Skipped" },
                    { key: "failed", header: "Failed" },
                  ]}
                />
              </div>
            )}
            {executionLogRows.length > 0 && (
              <div style={{ marginTop: "var(--space-3)" }}>
                <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Execution Log</div>
                <Table
                  rowKey="_rowKey"
                  data={executionLogRows}
                  columns={[
                    { key: "entity_type", header: "Entity Type" },
                    { key: "entity_id", header: "Entity ID" },
                    { key: "action", header: "Action" },
                    { key: "detail", header: "Detail", render: (v) => v ?? "—" },
                  ]}
                />
              </div>
            )}
          </Section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="session-status-section" title="Session Status">
            <StatusSignal tier={statusTier(sessionData?.status)} label={sessionData?.status ?? "No Session"} />
          </RailSection>

          <RailSection id="progress-section" title="Progress">
            {sessionData ? (
              <InfoRow label="Stage" value={progressLabel(sessionData.status)} />
            ) : (
              <div className="confidence-label ref-group-empty">No session yet.</div>
            )}
          </RailSection>

          <RailSection id="statistics-section" title="Import Summary">
            {stats ? (
              <>
                <InfoRow label="Packages" value={stats.total_packages} />
                <InfoRow label="Valid" value={stats.valid_packages} />
                <InfoRow label="Invalid" value={stats.invalid_packages} />
                <InfoRow label="Warnings" value={stats.warning_packages} />
                <InfoRow label="Conflicts" value={stats.conflict_count} />
                <InfoRow label="Inserted" value={stats.inserted} />
                <InfoRow label="Updated" value={stats.updated} />
                <InfoRow label="Skipped" value={stats.skipped} />
                <InfoRow label="Failed" value={stats.failed} />
              </>
            ) : (
              <div className="confidence-label ref-group-empty">No session yet.</div>
            )}
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={sessionData ? `${sessionData.session_id} · ${sessionData.status}` : "No session"}
        metaPrimary={hasIncomingPackage ? `${counts.pumps + counts.seals + counts.installations + counts.documents} records` : "No package"}
        metaLabel="Status"
        metaValue={sessionData?.status ?? "—"}
      >
        <button type="button" className="btn-link" onClick={onValidate} disabled={!hasIncomingPackage || loadingAction === "validate"} data-od-id="action-bar-validate">
          {loadingAction === "validate" ? "Validating…" : "Validate"}
        </button>
        <button type="button" className="btn-link" onClick={onReview} disabled={!hasIncomingPackage || loadingAction === "review"} data-od-id="action-bar-review">
          {loadingAction === "review" ? "Reviewing…" : "Review"}
        </button>
        <button type="button" className="btn-link" onClick={onExecute} disabled={!sessionData || executing} data-od-id="action-bar-execute">
          {executing ? "Executing…" : "Execute"}
        </button>
        <button type="button" className="btn-link" onClick={onRefresh} disabled={!sessionData || loadingAction === "refresh" || executing} data-od-id="action-bar-refresh">
          {loadingAction === "refresh" ? "Refreshing…" : "Refresh"}
        </button>
        {firstPump && (
          <button type="button" className="btn-link" onClick={() => onNavigate?.("pump", { selectId: firstPump.tag_number })} data-od-id="action-bar-open-pump">
            Open Pump →
          </button>
        )}
        {firstSeal && (
          <button type="button" className="btn-link" onClick={() => onNavigate?.("seal", { selectId: firstSeal.seal_code })} data-od-id="action-bar-open-seal">
            Open Seal →
          </button>
        )}
        {firstInstallation && (
          <button type="button" className="btn-link" onClick={() => onNavigate?.("installation", { selectId: firstInstallation.installation_code })} data-od-id="action-bar-open-installation">
            Open Installation →
          </button>
        )}
        {firstDocument && (
          <button type="button" className="btn-primary" onClick={() => onNavigate?.("document", { selectId: firstDocument.document_code })} data-od-id="action-bar-open-document">
            Open Document
          </button>
        )}
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "knowledge-package"} onClose={() => setDrawer(null)} title="Knowledge Package">
        <KnowledgeReviewWorkspaceView knowledgePackage={knowledgePackageForDrawer} onNavigate={onNavigate} />
      </PumpWorkspaceDrawer>
    </div>
  );
}
