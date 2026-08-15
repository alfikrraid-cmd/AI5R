import { useRef, useState } from "react";
import { Badge, Button, EmptyState, Table } from "../../../design-system";
import { Section } from "./open-design";
import { dryRunPumpXlsx, executeImportSession } from "../../../api/ai5rClient";

/**
 * MWO-LTSA-DATA-IMPORT-UI-001B/-001C -- Pump Master XLSX drag/drop
 * dry-run + Approve panel.
 *
 * Built entirely from existing design-system/open-design primitives
 * (Section/Table/Badge/Button/EmptyState) -- no new design language, no new
 * CSS file, no new table/drawer component. Self-contained (its own local
 * state), mounted alongside the existing generic JSON Import flow in
 * ImportWorkspace.jsx -- that flow's own state/handlers/tests are untouched.
 *
 * Two real API calls, both already-existing pipeline entry points, never a
 * client-side re-computation of either:
 *   - dryRunPumpXlsx (ai5rClient.js -> POST /api/ltsa/import/pump-xlsx/
 *     dry-run -> API.import_cli.dry_run_import(), MWO-LTSA-DATA-IMPORT-
 *     UI-001A/-CLOSURE/-001B) -- now also persists the reviewed
 *     ImportSession server-side, so report.session_id is a real,
 *     look-up-able id, not just a label.
 *   - executeImportSession (ai5rClient.js, pre-existing -- the SAME
 *     function the generic JSON Import flow already calls) -> POST
 *     /api/ltsa/import/execute -> ImportWorker/execute_import(), reused
 *     completely unmodified. This component sends only session_id; it
 *     never re-uploads the file or resends parsed data -- Approve executes
 *     exactly what the stored session holds (import_cli.dry_run_import()'s
 *     own immutability contract).
 *
 * "Never silently discard rows": every row_issue the backend returns is
 * rendered (not capped); preview_rows is a real but capped (backend-side,
 * _PREVIEW_ROW_LIMIT) slice of the parsed rows, labeled as a preview so a
 * capped table is never mistaken for "this is everything".
 *
 * Approve gating: enabled only when report.approval_ready is true (the
 * same boolean execute_import()'s own REJECTED_INVALID gate enforces
 * server-side -- this button's disabled state is a UX convenience, not the
 * only protection; a bypassed/direct API call still gets refused
 * server-side). A native window.confirm() is the "confirmation before
 * execution" step this mission requires -- a real, functioning browser
 * gate, not a new modal component invented for one button. After a
 * result comes back (success or failure), Approve is hidden for this
 * report -- the session is now terminal (IMPORTED/FAILED, replay-guarded
 * server-side too, POST .../execute's own status check) -- a fresh
 * Analyze / Dry Run is required to review (and possibly approve) again.
 */

const PUMP_XLSX_EXTENSIONS = [".xlsx", ".xls"];

function hasSupportedExtension(filename) {
  const lower = (filename || "").toLowerCase();
  return PUMP_XLSX_EXTENSIONS.some((extension) => lower.endsWith(extension));
}

function CountBadge({ label, value, variant }) {
  return (
    <span style={{ marginRight: "var(--space-3, 12px)" }}>
      <Badge variant={variant}>{label}: {value}</Badge>
    </span>
  );
}

export default function PumpXlsxImportPanel() {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rejectMessage, setRejectMessage] = useState(null);
  const [approving, setApproving] = useState(false);
  const [approveError, setApproveError] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const inputRef = useRef(null);

  function acceptFile(candidate) {
    if (!candidate) return;
    setError(null);
    setRejectMessage(null);
    setReport(null);
    setExecutionResult(null);
    setApproveError(null);
    if (!hasSupportedExtension(candidate.name)) {
      setRejectMessage(`"${candidate.name}" is not a .xlsx/.xls file -- choose the real Pump Master workbook.`);
      setFile(null);
      return;
    }
    setFile(candidate);
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    acceptFile(event.dataTransfer?.files?.[0] ?? null);
  }

  function handleFileInputChange(event) {
    acceptFile(event.target.files?.[0] ?? null);
  }

  async function handleAnalyze() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setExecutionResult(null);
    setApproveError(null);
    try {
      const result = await dryRunPumpXlsx(file);
      if (!result?.success) {
        setError(result?.message || "Dry-run failed");
        setReport(null);
      } else {
        setReport(result.data);
      }
    } catch (apiError) {
      setError(apiError.message);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!report?.session_id) return;
    const confirmed = window.confirm(
      `Approve and execute this import?\n\n` +
        `${report.new_count} INSERT, ${report.update_count} UPDATE, ${report.duplicate_count} SKIP.\n` +
        `This writes to the live ltsa_pumps table and cannot be undone.`
    );
    if (!confirmed) return;

    setApproving(true);
    setApproveError(null);
    try {
      const result = await executeImportSession(report.session_id);
      if (!result?.success) {
        setApproveError(result?.message || "Approve failed");
      } else {
        setExecutionResult(result.data);
      }
    } catch (apiError) {
      setApproveError(apiError.message);
    } finally {
      setApproving(false);
    }
  }

  const approvalReady = report?.approval_ready === true;
  const canApprove = approvalReady && !approving && !executionResult;

  return (
    <Section id="pump-xlsx-import-section" title="Pump Master XLSX Import">
      <div
        data-testid="pump-xlsx-dropzone"
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${dragActive ? "#3B82F6" : "#1F2937"}`,
          borderRadius: 8,
          padding: "var(--space-4, 24px)",
          textAlign: "center",
          marginTop: "var(--space-3, 12px)",
          cursor: "pointer",
        }}
        onClick={() => inputRef.current?.click()}
      >
        <p style={{ margin: 0, color: "#94A3B8" }}>
          Drag &amp; drop the Pump Master .xlsx file here, or click to choose a file.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          aria-label="Upload Pump Master XLSX"
          onChange={handleFileInputChange}
          style={{ display: "none" }}
        />
      </div>

      {file && <p data-testid="pump-xlsx-filename">{file.name}</p>}
      {rejectMessage && <p data-testid="pump-xlsx-reject-message" style={{ color: "#EF4444" }}>{rejectMessage}</p>}

      <div style={{ marginTop: "var(--space-3, 12px)" }}>
        <Button onClick={handleAnalyze} disabled={!file || loading}>
          {loading ? "Analyzing..." : "Analyze / Dry Run"}
        </Button>
      </div>

      {error && <p data-testid="pump-xlsx-error" style={{ color: "#EF4444" }}>{error}</p>}

      {report && (
        <div data-testid="pump-xlsx-report" style={{ marginTop: "var(--space-4, 24px)" }}>
          <p>
            <strong>{report.source}</strong> -- sheet: {report.sheet ?? "(none)"}
          </p>
          <p>
            source_count: {report.source_count} · normalized_count: {report.normalized_count}
          </p>

          <div style={{ marginBottom: "var(--space-3, 12px)" }}>
            <CountBadge label="Valid" value={report.valid_count} variant="success" />
            <CountBadge label="Warning" value={report.warning_count} variant="warning" />
            <CountBadge label="Rejected" value={report.rejected_count} variant="danger" />
          </div>

          <div style={{ marginBottom: "var(--space-3, 12px)" }}>
            <CountBadge label="INSERT" value={report.new_count} variant="info" />
            <CountBadge label="UPDATE" value={report.update_count} variant="warning" />
            <CountBadge label="SKIP" value={report.duplicate_count} variant="purple" />
          </div>

          <p data-testid="pump-xlsx-approval-ready">
            approval_ready: <Badge variant={approvalReady ? "success" : "danger"}>{String(approvalReady)}</Badge>
          </p>

          <Section id="pump-xlsx-mapping-section" title="Column Mapping">
            <p>Mapped: {Object.entries(report.mapped_columns).map(([source, canonical]) => `${source} -> ${canonical}`).join(", ") || "(none)"}</p>
            <p>Unmapped (not imported): {report.unmapped_columns.join(", ") || "(none)"}</p>
          </Section>

          <Section id="pump-xlsx-issues-section" title={`Row Issues (${report.row_issues.length})`}>
            {report.row_issues.length > 0 ? (
              <Table
                rowKey="_issueKey"
                data={report.row_issues.map((issue, index) => ({ ...issue, _issueKey: index }))}
                columns={[
                  {
                    key: "severity",
                    header: "Severity",
                    render: (value) => <Badge variant={value === "ERROR" ? "danger" : "warning"}>{value}</Badge>,
                  },
                  { key: "entity_id", header: "Tag" },
                  { key: "message", header: "Reason" },
                ]}
              />
            ) : (
              <p>No row issues.</p>
            )}
          </Section>

          <Section id="pump-xlsx-preview-section" title={`Preview Rows (first ${report.preview_rows.length})`}>
            {report.preview_rows.length > 0 ? (
              <Table
                rowKey="_previewKey"
                data={report.preview_rows.map((row, index) => ({ ...row, _previewKey: index }))}
                columns={[
                  { key: "tag_number", header: "Tag Number" },
                  { key: "area", header: "Area" },
                  { key: "pump_type", header: "Pump Type" },
                  { key: "api_plan", header: "API Plan" },
                ]}
              />
            ) : (
              <EmptyState title="No rows parsed" description="The workbook produced no pump rows to preview." />
            )}
          </Section>

          {!executionResult && (
            <div style={{ marginTop: "var(--space-3, 12px)" }}>
              <Button onClick={handleApprove} disabled={!canApprove}>
                {approving ? "Approving..." : "Approve Import"}
              </Button>
              {!approvalReady && (
                <p data-testid="pump-xlsx-approve-note" style={{ color: "#94A3B8" }}>
                  Approve is disabled -- resolve the rejected rows above first (all-or-nothing: {report.rejected_count} rejected row(s) block the entire import).
                </p>
              )}
            </div>
          )}

          {approveError && <p data-testid="pump-xlsx-approve-error" style={{ color: "#EF4444" }}>{approveError}</p>}

          {executionResult && (
            <Section id="pump-xlsx-execution-result-section" title="Execution Result">
              <div data-testid="pump-xlsx-execution-result">
                <p>
                  session_id: {executionResult.session_id} · status:{" "}
                  <Badge variant={executionResult.status === "COMMITTED" ? "success" : "danger"}>
                    {executionResult.status}
                  </Badge>
                </p>
                {executionResult.reason && <p>{executionResult.reason}</p>}
                {executionResult.statistics?.pump && (
                  <div>
                    <CountBadge label="Inserted" value={executionResult.statistics.pump.inserted} variant="info" />
                    <CountBadge label="Updated" value={executionResult.statistics.pump.updated} variant="warning" />
                    <CountBadge label="Skipped" value={executionResult.statistics.pump.skipped} variant="purple" />
                    <CountBadge label="Failed" value={executionResult.statistics.pump.failed} variant="danger" />
                  </div>
                )}
              </div>
            </Section>
          )}
        </div>
      )}
    </Section>
  );
}
