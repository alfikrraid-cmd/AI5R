import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import ConditionMonitoringMeasurementFieldsForm from "./ConditionMonitoringMeasurementFieldsForm";
import AssetSelector from "./AssetSelector";
import { getPumps, createAdHocConditionMonitoringReadingsBulk } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import {
  countRecordedMeasurements,
  emptyBulkCmonRow,
  toBulkAdHocPayload,
  validateBulkCmonRows,
} from "../utils/cmonBulkReading";

// MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- browser-based bulk Condition
// Monitoring reading editor, mirroring BulkPMScheduleEditor.jsx's own
// proven Edit -> Validate -> Review -> Confirm Create shape (a dedicated
// full-width view, not a cramped modal), but CMON semantics stay
// independent: no schedule/frequency/trigger-type at all (every row is
// ad-hoc by construction), no "Apply Activities"-style bulk value
// propagation (Section 5's own "Safer default: NO bulk measurement
// propagation" -- copying 37 measurement fields across rows implicitly
// would be far riskier than copying 4 PM schedule fields, so this editor
// simply does not offer it). Apply-to-Selected exists ONLY for Reading
// Date -- the one field a technician doing a walk-around genuinely
// shares across multiple pumps; Finding/Notes and every measurement stay
// strictly per-row.

const inputStyle = {
  width: "100%",
  minWidth: 90,
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.xs}px`,
  boxSizing: "border-box",
  fontSize: 12,
};

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
  fontSize: 12,
  whiteSpace: "nowrap",
};

const tdStyle = { padding: spacing.xs, verticalAlign: "top", borderBottom: `1px solid ${colors.border}` };
const errorTextStyle = { color: colors.danger, fontSize: 11, margin: `${spacing.xs}px 0 0 0` };

// MWO-LTSA-CMON-EXCEL-IMPORT-001 -- "Excel row 17: ..." style prefix for
// any message rendered against a row that came from an import, matching
// pmBulkSchedule's own established convention. A manually-added row's
// source/sourceRow are both null, so this is a no-op for it.
function sourcePrefix(row) {
  return row.source === "EXCEL_IMPORT" && row.sourceRow != null ? `Excel row ${row.sourceRow}: ` : "";
}

function StatusBadge({ level }) {
  if (!level) {
    return <span style={{ color: colors.textMuted, fontSize: 11 }}>Not validated</span>;
  }
  const palette = { READY: colors.success, ERROR: colors.danger };
  const label = { READY: "Ready", ERROR: "Error" }[level];
  return <span style={{ color: palette[level], fontWeight: 600, fontSize: 11 }}>{label}</span>;
}

// Compact "N recorded [Edit]" cell instead of rendering all 37
// measurement inputs as permanent table columns (Section 5's own
// "avoid an unusably-wide 30+ measurement-column table").
function MeasurementsCell({ measurements, onEdit }) {
  const count = countRecordedMeasurements(measurements);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
      <span style={{ fontSize: 12, color: colors.text }}>{count} recorded</span>
      <Button type="button" onClick={onEdit}>
        Edit
      </Button>
    </div>
  );
}

// MWO-LTSA-CMON-EXCEL-IMPORT-001 -- `initialRows` seeds the SAME row
// model Excel import produces (utils/conditionMonitoringExcelImport.js's
// own buildImportPreview()) so imported rows are edited exactly like
// manually-added ones -- no second editor, no Excel-specific creation
// path. Their ids already use a distinct "import-row-" prefix from this
// component's own "bulk-cmon-row-" counter, so no collision risk when
// more rows are added manually afterward.
export default function BulkCMONReadingEditor({ onClose, onCreated, initialRows = [] }) {
  const idCounter = useRef(0);
  function nextId() {
    idCounter.current += 1;
    return `bulk-cmon-row-${idCounter.current}`;
  }

  const [rows, setRows] = useState(initialRows);
  const [validation, setValidation] = useState(null);
  const [dirty, setDirty] = useState(true);

  const [pumps, setPumps] = useState([]);
  const [pumpsLoading, setPumpsLoading] = useState(true);
  const [pumpsError, setPumpsError] = useState(null);

  const [multiPumpOpen, setMultiPumpOpen] = useState(false);
  const [multiPumpSelection, setMultiPumpSelection] = useState(new Set());

  const [applyReadingDate, setApplyReadingDate] = useState("");
  const [rowMeasurementEditorId, setRowMeasurementEditorId] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    let active = true;
    setPumpsLoading(true);
    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) setPumps(mapped);
      })
      .catch((error) => {
        if (active) setPumpsError(error?.message || "Pumps could not be loaded.");
      })
      .finally(() => {
        if (active) setPumpsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const canonicalPumpTags = new Set(pumps.map((p) => p.tag));
  const selectedRows = rows.filter((r) => r.selected);

  // Any row-data mutation invalidates a prior validation result --
  // mirrors BulkPMScheduleEditor's own Section H discipline exactly.
  function mutateRows(updater) {
    setRows(updater);
    setValidation(null);
    setDirty(true);
  }

  function addRow() {
    mutateRows((current) => [...current, emptyBulkCmonRow(nextId())]);
  }

  function removeRow(id) {
    mutateRows((current) => current.filter((r) => r.id !== id));
  }

  function duplicateRow(id) {
    mutateRows((current) => {
      const index = current.findIndex((r) => r.id === id);
      if (index === -1) return current;
      const clone = { ...current[index], id: nextId(), selected: false, measurements: { ...current[index].measurements } };
      const next = [...current];
      next.splice(index + 1, 0, clone);
      return next;
    });
  }

  // MWO-LTSA-CMON-EXCEL-IMPORT-001 -- a manual edit clears any stale
  // Excel-import-time errors on that row: the user just corrected the
  // field, so re-flagging the old parse-time problem after Validate
  // re-runs would permanently block a row the human already fixed.
  function updateRowField(id, field, value) {
    mutateRows((current) => current.map((r) => (r.id === id ? { ...r, [field]: value, importErrors: [] } : r)));
  }

  function setRowMeasurementField(id, name) {
    return (event) =>
      mutateRows((current) =>
        current.map((r) =>
          r.id === id
            ? { ...r, measurements: { ...r.measurements, [name]: event.target.value }, importErrors: [] }
            : r
        )
      );
  }

  function toggleRowSelected(id) {
    setRows((current) => current.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r)));
  }

  function selectAll() {
    setRows((current) => current.map((r) => ({ ...r, selected: true })));
  }

  function clearSelection() {
    setRows((current) => current.map((r) => ({ ...r, selected: false })));
  }

  function openMultiPumpPicker() {
    setMultiPumpSelection(new Set());
    setMultiPumpOpen(true);
  }

  function toggleMultiPumpTag(tag) {
    setMultiPumpSelection((current) => {
      const next = new Set(current);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  }

  // "Select Pumps -> choose multiple canonical pumps -> one row per
  // selection", reusing the SAME canonical pump list AssetSelector/
  // getPumps() already load. Set-based selection naturally prevents
  // adding the exact same pump twice from this picker in one action.
  function addRowsForSelectedPumps() {
    const tags = Array.from(multiPumpSelection);
    mutateRows((current) => [...current, ...tags.map((tag) => emptyBulkCmonRow(nextId(), { pumpTag: tag }))]);
    setMultiPumpOpen(false);
  }

  // Apply-to-Selected covers ONLY Reading Date -- the one field this
  // domain treats as genuinely shared across a batch. A blank apply
  // value means "leave selected rows' dates alone"; unselected rows are
  // never touched.
  function applyReadingDateToSelected() {
    if (!applyReadingDate) return;
    mutateRows((current) => current.map((row) => (row.selected ? { ...row, readingDate: applyReadingDate } : row)));
  }

  function handleValidate() {
    const result = validateBulkCmonRows(rows, { canonicalPumpTags });
    setValidation(result);
    setDirty(false);
  }

  const canConfirm = rows.length > 0 && validation !== null && !dirty && validation.summary.errors === 0 && !submitting;

  async function handleConfirm() {
    if (!canConfirm) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = toBulkAdHocPayload(rows);
      const result = await createAdHocConditionMonitoringReadingsBulk(payload.readings);
      onCreated?.(result.data);
    } catch (error) {
      setSubmitError(error.message);
      setDirty(true);
    } finally {
      setSubmitting(false);
    }
  }

  const rowMeasurementEditorRow = rows.find((r) => r.id === rowMeasurementEditorId) || null;

  return (
    <div data-testid="bulk-cmon-reading-editor">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md }}>
        <div>
          <h1 style={{ margin: 0, color: colors.text }}>Bulk Condition Monitoring Reading</h1>
          <p style={{ margin: 0, color: colors.textMuted, fontSize: 12 }}>
            Every row is an ad-hoc reading -- no Condition Monitoring schedule is required.
          </p>
        </div>
        <Button type="button" onClick={onClose}>
          Back to Condition Monitoring
        </Button>
      </div>

      {submitError ? (
        <p role="alert" style={{ ...errorTextStyle, fontSize: 13, marginBottom: spacing.sm }}>
          {submitError}
        </p>
      ) : null}

      <div style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap", marginBottom: spacing.sm }}>
        <Button type="button" onClick={addRow}>
          + Add Row
        </Button>
        <Button type="button" onClick={openMultiPumpPicker} disabled={pumpsLoading || Boolean(pumpsError)}>
          + Add Pumps...
        </Button>
        <Button type="button" onClick={selectAll} disabled={rows.length === 0}>
          Select All
        </Button>
        <Button type="button" onClick={clearSelection} disabled={selectedRows.length === 0}>
          Clear Selection
        </Button>
      </div>

      {selectedRows.length > 0 ? (
        <div style={{ border: `1px solid ${colors.border}`, borderRadius: spacing.xs, padding: spacing.sm, marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
            Apply to {selectedRows.length} selected row{selectedRows.length === 1 ? "" : "s"} (Reading Date only --
            measurements and Finding/Notes are never bulk-copied):
          </div>
          <div style={{ display: "flex", gap: spacing.xs, flexWrap: "wrap", alignItems: "center" }}>
            <input
              aria-label="Apply Reading Date"
              type="date"
              style={inputStyle}
              value={applyReadingDate}
              onChange={(e) => setApplyReadingDate(e.target.value)}
            />
            <Button type="button" onClick={applyReadingDateToSelected} disabled={!applyReadingDate}>
              Apply to Selected
            </Button>
          </div>
        </div>
      ) : null}

      <div style={{ overflowX: "auto" }}>
        {rows.length === 0 ? (
          <p style={{ color: colors.textMuted }}>No rows yet. Use "+ Add Row" or "+ Add Pumps..." to begin.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={thStyle}>Select</th>
                <th style={thStyle}>Pump *</th>
                <th style={thStyle}>Reading Date *</th>
                <th style={thStyle}>Measurements</th>
                <th style={thStyle}>Finding / Notes</th>
                <th style={thStyle}>Validation</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const result = validation?.results[row.id];
                return (
                  <tr key={row.id} data-testid={`bulk-cmon-row-${row.id}`}>
                    <td style={tdStyle}>
                      <input
                        type="checkbox"
                        aria-label={`Select row ${row.id}`}
                        checked={row.selected}
                        onChange={() => toggleRowSelected(row.id)}
                      />
                    </td>
                    <td style={tdStyle}>
                      {pumpsLoading ? (
                        <span style={{ color: colors.textMuted, fontSize: 12 }}>Loading...</span>
                      ) : pumpsError ? (
                        <span style={errorTextStyle}>{pumpsError}</span>
                      ) : (
                        <AssetSelector
                          id={`bulk-cmon-pump-${row.id}`}
                          label="Pump"
                          assets={pumps.map((p) => ({ tag: p.tag, name: p.name }))}
                          selectedTag={row.pumpTag || null}
                          onSelect={(tag) => updateRowField(row.id, "pumpTag", tag || "")}
                        />
                      )}
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Reading Date for row ${row.id}`}
                        type="date"
                        style={inputStyle}
                        value={row.readingDate}
                        onChange={(e) => updateRowField(row.id, "readingDate", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <MeasurementsCell measurements={row.measurements} onEdit={() => setRowMeasurementEditorId(row.id)} />
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Finding for row ${row.id}`}
                        style={inputStyle}
                        value={row.finding}
                        onChange={(e) => updateRowField(row.id, "finding", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <StatusBadge level={result?.level} />
                      {/* MWO-LTSA-CMON-EXCEL-IMPORT-001 -- import-time
                          problems (invalid numeric text, an unrecognized
                          leak token -- no valid slot in the structured
                          row) are shown ALONGSIDE live validateBulkCmonRows()
                          errors, both prefixed with the originating Excel
                          row when this row came from an import. */}
                      {row.importErrors?.map((message, i) => (
                        <p key={`import-err-${i}`} style={errorTextStyle}>
                          {sourcePrefix(row)}
                          {message}
                        </p>
                      ))}
                      {result?.errors.map((message, i) => (
                        <p key={`err-${i}`} style={errorTextStyle}>
                          {sourcePrefix(row)}
                          {message}
                        </p>
                      ))}
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", gap: spacing.xs }}>
                        <Button type="button" onClick={() => duplicateRow(row.id)}>
                          Duplicate
                        </Button>
                        <Button type="button" onClick={() => removeRow(row.id)}>
                          Remove
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: spacing.md,
          flexWrap: "wrap",
          gap: spacing.sm,
        }}
      >
        <div style={{ color: colors.textMuted, fontSize: 13 }}>
          {validation ? (
            <span data-testid="bulk-cmon-validation-summary">
              Rows: {validation.summary.rows} · Ready: {validation.summary.ready} · Errors: {validation.summary.errors}
            </span>
          ) : (
            <span>Not yet validated.</span>
          )}
        </div>
        <div style={{ display: "flex", gap: spacing.sm }}>
          <Button type="button" onClick={handleValidate} disabled={rows.length === 0}>
            Validate
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={!canConfirm}>
            Confirm Create
          </Button>
        </div>
      </div>

      {multiPumpOpen ? (
        <Modal isOpen onClose={() => setMultiPumpOpen(false)} title="Select Pumps">
          <p style={{ color: colors.textMuted, fontSize: 12 }}>
            Choose one or more canonical pumps -- one row is generated per selection.
          </p>
          <div style={{ maxHeight: 320, overflowY: "auto", border: `1px solid ${colors.border}`, borderRadius: spacing.xs }}>
            {pumps.map((pump) => (
              <label
                key={pump.tag}
                style={{ display: "flex", alignItems: "center", gap: spacing.xs, padding: spacing.xs, color: colors.text }}
              >
                <input
                  type="checkbox"
                  checked={multiPumpSelection.has(pump.tag)}
                  onChange={() => toggleMultiPumpTag(pump.tag)}
                />
                {pump.tag} — {pump.name}
              </label>
            ))}
          </div>
          <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end", marginTop: spacing.md }}>
            <Button type="button" onClick={() => setMultiPumpOpen(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={addRowsForSelectedPumps} disabled={multiPumpSelection.size === 0}>
              Add {multiPumpSelection.size || ""} Row{multiPumpSelection.size === 1 ? "" : "s"}
            </Button>
          </div>
        </Modal>
      ) : null}

      {rowMeasurementEditorRow ? (
        <Modal
          isOpen
          onClose={() => setRowMeasurementEditorId(null)}
          title={`Measurements -- ${rowMeasurementEditorRow.pumpTag || "row"}`}
        >
          <ConditionMonitoringMeasurementFieldsForm
            measurements={rowMeasurementEditorRow.measurements}
            onFieldChange={(name) => setRowMeasurementField(rowMeasurementEditorRow.id, name)}
            idPrefix={`bulk-cmon-${rowMeasurementEditorRow.id}`}
          />
        </Modal>
      ) : null}
    </div>
  );
}
