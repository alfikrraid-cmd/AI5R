import { useRef, useState } from "react";
import { Badge, Button, EmptyState, Table } from "../../../design-system";
import { Section } from "./open-design";
import { dryRunPumpXlsx } from "../../../api/ai5rClient";

/**
 * MWO-LTSA-DATA-IMPORT-UI-001B -- Pump Master XLSX drag/drop dry-run panel.
 *
 * Built entirely from existing design-system/open-design primitives
 * (Section/Table/Badge/Button/EmptyState) -- no new design language, no new
 * CSS file, no new table/drawer component. Self-contained (its own local
 * state), mounted alongside the existing generic JSON Import flow in
 * ImportWorkspace.jsx -- that flow's own state/handlers/tests are untouched.
 *
 * One real API call (dryRunPumpXlsx, ai5rClient.js -> POST /api/ltsa/import/
 * pump-xlsx/dry-run -> API.import_cli.dry_run_import(), reused unmodified)
 * per "Analyze / Dry Run" click. This component never parses the workbook
 * itself, never re-validates, never re-plans -- it only renders the real
 * DryRunReport the backend returns, exactly as returned.
 *
 * "Never silently discard rows": every row_issue the backend returns is
 * rendered (not capped); preview_rows is a real but capped (backend-side,
 * _PREVIEW_ROW_LIMIT) slice of the parsed rows, labeled as a preview so a
 * capped table is never mistaken for "this is everything".
 *
 * Approve: disabled unconditionally in this mission. The dry-run pipeline
 * never persists a session (by design -- see dry_run_import()'s own
 * "zero persistent writes" contract), so there is no session_id the
 * existing POST /api/ltsa/import/execute endpoint could act on yet.
 * Wiring that safely (session hand-off from a dry-run to a real execute
 * call) is real, disclosed, out-of-scope work for MWO-LTSA-DATA-IMPORT-
 * UI-001C -- not invented here.
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
  const inputRef = useRef(null);

  function acceptFile(candidate) {
    if (!candidate) return;
    setError(null);
    setRejectMessage(null);
    setReport(null);
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

  const approvalReady = report?.approval_ready === true;

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

          <div style={{ marginTop: "var(--space-3, 12px)" }}>
            <Button disabled>Approve Import</Button>
            <p data-testid="pump-xlsx-approve-note" style={{ color: "#94A3B8" }}>
              {approvalReady
                ? "Approve execution is deferred to MWO-LTSA-DATA-IMPORT-UI-001C (session hand-off to the execute pipeline is not yet wired)."
                : "Approve is disabled -- resolve the rejected rows above first."}
            </p>
          </div>
        </div>
      )}
    </Section>
  );
}
