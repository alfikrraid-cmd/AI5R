import { useRef, useState } from "react";
import { Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { getPumps, parsePMScheduleExcel, downloadPMScheduleImportTemplate } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import { buildImportPreview } from "../utils/pmExcelImport";

const errorTextStyle = { color: colors.danger, fontSize: 13, margin: `${spacing.xs}px 0` };
const warningTextStyle = { color: colors.warning, fontSize: 13, margin: `${spacing.xs}px 0` };

// AI5R-PHASE4E4 -- MANDATORY FLOW: Excel -> parse -> map -> Bulk Editor
// -> validate -> human review/correction -> Confirm Create -> the
// existing atomic bulk endpoint. This component does ONLY the first two
// steps (upload/parse/preview) -- it never calls bulkCreatePMSchedules
// itself, has no Confirm-style action of its own, and the ONLY way rows
// leave this component is onReviewInBulkEditor(rows), which hands them
// to the SAME BulkPMScheduleEditor 4E.3 built (Section B: "Do not
// duplicate Bulk Editor"). Structural workbook problems (missing
// required columns, >1000 rows) stop here entirely -- "Review in Bulk
// Editor" simply does not render for them (Section J: "do not
// continue"). Row-level problems are attached to individual rows by
// buildImportPreview() and DO proceed into the Bulk Editor, so the user
// can correct them there instead of losing the row (Section J).
export default function PMExcelImportPanel({ onClose, onReviewInBulkEditor }) {
  const [file, setFile] = useState(null);
  const [rejectMessage, setRejectMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [parseError, setParseError] = useState(null);
  const [templateError, setTemplateError] = useState(null);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const inputRef = useRef(null);
  const idCounter = useRef(0);

  function makeRowId() {
    idCounter.current += 1;
    return `import-row-${idCounter.current}`;
  }

  function acceptFile(candidate) {
    if (!candidate) {
      return;
    }
    setParseError(null);
    setPreview(null);
    const lowerName = (candidate.name || "").toLowerCase();
    // Section C -- .xlsx only; legacy .xls is deliberately never accepted.
    if (!lowerName.endsWith(".xlsx")) {
      setRejectMessage(`"${candidate.name}" is not a .xlsx file -- only .xlsx is supported.`);
      setFile(null);
      return;
    }
    setRejectMessage(null);
    setFile(candidate);
  }

  function handleFileInputChange(event) {
    acceptFile(event.target.files?.[0] ?? null);
  }

  function handleDrop(event) {
    event.preventDefault();
    acceptFile(event.dataTransfer?.files?.[0] ?? null);
  }

  async function handleParse() {
    if (!file) {
      return;
    }
    setLoading(true);
    setParseError(null);
    setPreview(null);
    try {
      const [parseResult, pumpRecords] = await Promise.all([
        parsePMScheduleExcel(file),
        getPumps().then((records) => records.map(mapPumpRecord)),
      ]);
      const canonicalPumpTags = new Set(pumpRecords.map((pump) => pump.tag));
      const result = buildImportPreview(parseResult.data, { canonicalPumpTags, makeRowId });
      setPreview(result);
    } catch (error) {
      setParseError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadTemplate() {
    setDownloadingTemplate(true);
    setTemplateError(null);
    try {
      const blob = await downloadPMScheduleImportTemplate();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "pm_schedule_import_template.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      setTemplateError(error.message);
    } finally {
      setDownloadingTemplate(false);
    }
  }

  const canReview = Boolean(preview && !preview.structuralError && preview.rows?.length > 0);

  return (
    <div data-testid="pm-excel-import-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md }}>
        <div>
          <h1 style={{ margin: 0, color: colors.text }}>Import Excel</h1>
          <p style={{ margin: 0, color: colors.textMuted, fontSize: 12 }}>
            Parsed rows are reviewed and corrected in the Bulk Schedule editor -- nothing is created here.
          </p>
        </div>
        <Button type="button" onClick={onClose}>
          Back to PM Schedules
        </Button>
      </div>

      <div style={{ marginBottom: spacing.md }}>
        <Button type="button" onClick={handleDownloadTemplate} disabled={downloadingTemplate}>
          {downloadingTemplate ? "Downloading..." : "Download Excel Template"}
        </Button>
        {templateError ? (
          <p role="alert" style={errorTextStyle}>
            {templateError}
          </p>
        ) : null}
      </div>

      <div
        data-testid="pm-excel-dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${colors.border}`,
          borderRadius: spacing.xs,
          padding: spacing.lg,
          textAlign: "center",
          cursor: "pointer",
        }}
      >
        <p style={{ margin: 0, color: colors.textMuted }}>
          Drag &amp; drop the PM Schedule .xlsx file here, or click to choose a file.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          aria-label="Upload PM Schedule Excel file"
          onChange={handleFileInputChange}
          style={{ display: "none" }}
        />
      </div>

      {file ? <p style={{ color: colors.text }}>{file.name}</p> : null}
      {rejectMessage ? (
        <p role="alert" style={errorTextStyle}>
          {rejectMessage}
        </p>
      ) : null}

      <div style={{ marginTop: spacing.md }}>
        <Button type="button" onClick={handleParse} disabled={!file || loading}>
          {loading ? "Parsing..." : "Parse File"}
        </Button>
      </div>

      {parseError ? (
        <p role="alert" style={errorTextStyle}>
          {parseError}
        </p>
      ) : null}

      {preview ? (
        <div data-testid="pm-excel-import-preview" style={{ marginTop: spacing.md }}>
          <p style={{ color: colors.text }}>File: {file?.name}</p>
          {preview.structuralError ? (
            <p role="alert" style={errorTextStyle}>
              {preview.structuralError}
            </p>
          ) : (
            <>
              <p style={{ color: colors.text }}>Rows detected: {preview.rowCount}</p>
              <p style={{ color: colors.text }}>Mapped: {preview.mappedColumns.length} column(s)</p>
              <p style={{ color: colors.text }}>Warnings: {preview.warnings.length}</p>
              <p style={{ color: colors.text }}>Errors: {preview.importErrorCount}</p>
              {preview.warnings.map((warning, index) => (
                <p key={index} style={warningTextStyle}>
                  {warning}
                </p>
              ))}
              <Button type="button" onClick={() => onReviewInBulkEditor(preview.rows)} disabled={!canReview}>
                Review in Bulk Editor
              </Button>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
