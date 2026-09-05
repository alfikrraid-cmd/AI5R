import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import PMActivityFamilyChecklist from "./PMActivityFamilyChecklist";
import AssetSelector from "./AssetSelector";
import { getPumps, bulkCreatePMSchedules } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import {
  SUPPORTED_FREQUENCIES,
  countPlannedActivities,
  emptyBulkRow,
  toBulkCreatePayload,
  validateBulkRows,
} from "../utils/pmBulkSchedule";

const FREQUENCY_OPTIONS = [
  { value: "", label: "Select..." },
  { value: "DAILY", label: "Daily" },
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "RUNTIME_BASED", label: "Runtime-based" },
];

const APPLY_FREQUENCY_OPTIONS = FREQUENCY_OPTIONS; // same list, "" means "don't change"

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
const warningTextStyle = { color: colors.warning, fontSize: 11, margin: `${spacing.xs}px 0 0 0` };

function StatusBadge({ level }) {
  if (!level) {
    return <span style={{ color: colors.textMuted, fontSize: 11 }}>Not validated</span>;
  }
  const palette = { READY: colors.success, WARNING: colors.warning, ERROR: colors.danger };
  const label = { READY: "Ready", WARNING: "Warning", ERROR: "Error" }[level];
  return <span style={{ color: palette[level], fontWeight: 600, fontSize: 11 }}>{label}</span>;
}

// AI5R-PHASE4E3, Section N -- compact Activities cell ("N selected
// [Edit]") instead of rendering all 19 checkboxes as permanent table
// columns. Opening [Edit] shows the same grouped 7-family
// PMActivityFamilyChecklist the single-create flow already uses.
function ActivitiesCell({ plannedMap, onEdit }) {
  const count = countPlannedActivities(plannedMap);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
      <span style={{ fontSize: 12, color: colors.text }}>{count} selected</span>
      <Button type="button" onClick={onEdit}>
        Edit
      </Button>
    </div>
  );
}

function ActivityEditorModal({ title, plannedMap, onToggle, onClose, onApply, applyLabel }) {
  return (
    <Modal isOpen onClose={onClose} title={title}>
      <PMActivityFamilyChecklist doneMap={plannedMap} onToggle={onToggle} />
      <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end", marginTop: spacing.md }}>
        <Button type="button" onClick={onClose}>
          Cancel
        </Button>
        {onApply ? (
          <Button type="button" onClick={onApply}>
            {applyLabel}
          </Button>
        ) : null}
      </div>
    </Modal>
  );
}

// AI5R-PHASE4E3 -- browser-based bulk PM schedule editor: edit rows ->
// Validate -> review the summary -> Confirm Create. This is a dedicated
// full-width view (not a cramped modal), matching Section N's "practical
// for ~10-100 rows" requirement. No schedule is created while editing --
// only Confirm Create (Section C, Section H) ever calls the backend, and
// only after a clean (or warning-only) Validate pass with no rows changed
// since (Section H: "Changing any validated row invalidates prior
// validation").
export default function BulkPMScheduleEditor({ onClose, onCreated, existingSchedules = [] }) {
  const idCounter = useRef(0);
  function nextId() {
    idCounter.current += 1;
    return `bulk-row-${idCounter.current}`;
  }

  const [rows, setRows] = useState([]);
  const [validation, setValidation] = useState(null);
  const [dirty, setDirty] = useState(true);

  const [pumps, setPumps] = useState([]);
  const [pumpsLoading, setPumpsLoading] = useState(true);
  const [pumpsError, setPumpsError] = useState(null);

  const [multiPumpOpen, setMultiPumpOpen] = useState(false);
  const [multiPumpSelection, setMultiPumpSelection] = useState(new Set());

  const [applyForm, setApplyForm] = useState({ frequency: "", startDate: "", technician: "", duration: "", notes: "" });
  const [rowActivityEditorId, setRowActivityEditorId] = useState(null);
  const [applyActivitiesOpen, setApplyActivitiesOpen] = useState(false);
  const [applyActivitiesMap, setApplyActivitiesMap] = useState({});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [serverRowErrors, setServerRowErrors] = useState({});

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

  // AI5R-PHASE4E3, Section H -- any row-data mutation invalidates any
  // prior validation result; only selection toggling (which changes
  // nothing about to be submitted) is exempt, see toggleRowSelected below.
  function mutateRows(updater) {
    setRows(updater);
    setValidation(null);
    setDirty(true);
  }

  function addRow() {
    mutateRows((current) => [...current, emptyBulkRow(nextId())]);
  }

  function removeRow(id) {
    mutateRows((current) => current.filter((r) => r.id !== id));
  }

  function duplicateRow(id) {
    mutateRows((current) => {
      const index = current.findIndex((r) => r.id === id);
      if (index === -1) return current;
      const clone = { ...current[index], id: nextId(), selected: false, plannedMap: { ...current[index].plannedMap } };
      const next = [...current];
      next.splice(index + 1, 0, clone);
      return next;
    });
  }

  function updateRowField(id, field, value) {
    mutateRows((current) => current.map((r) => (r.id === id ? { ...r, [field]: value } : r)));
  }

  function toggleRowActivity(id, code) {
    mutateRows((current) =>
      current.map((r) => (r.id === id ? { ...r, plannedMap: { ...r.plannedMap, [code]: !r.plannedMap[code] } } : r))
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

  // AI5R-PHASE4E3, Section D -- "Select Pumps -> choose multiple canonical
  // pumps -> generate one row per selected pump", reusing the SAME
  // canonical pump list AssetSelector/getPumps() already load (never a
  // second pump master implementation).
  function addRowsForSelectedPumps() {
    const tags = Array.from(multiPumpSelection);
    mutateRows((current) => [...current, ...tags.map((tag) => emptyBulkRow(nextId(), { pumpTag: tag }))]);
    setMultiPumpOpen(false);
  }

  // AI5R-PHASE4E3, Section E -- only SELECTED rows are touched; a blank
  // apply-field means "leave this field alone" even for selected rows, so
  // a half-filled apply form never blanks out existing values. Unselected
  // rows are never touched (same array reference returned for them).
  function applyToSelected() {
    mutateRows((current) =>
      current.map((row) => {
        if (!row.selected) return row;
        const next = { ...row };
        if (applyForm.frequency) next.frequency = applyForm.frequency;
        if (applyForm.startDate) next.startDate = applyForm.startDate;
        if (applyForm.technician) next.technician = applyForm.technician;
        if (applyForm.duration !== "") next.duration = applyForm.duration;
        if (applyForm.notes) next.notes = applyForm.notes;
        return next;
      })
    );
  }

  // Section E -- "Applying activities REPLACES planned activities only
  // after explicit user action": this function only ever runs from the
  // Apply Activities modal's own "Apply to Selected" button click.
  function applyActivitiesToSelected() {
    mutateRows((current) =>
      current.map((row) => (row.selected ? { ...row, plannedMap: { ...applyActivitiesMap } } : row))
    );
    setApplyActivitiesOpen(false);
  }

  function handleValidate() {
    const result = validateBulkRows(rows, { canonicalPumpTags, existingActiveSchedules: existingSchedules });
    setValidation(result);
    setDirty(false);
  }

  const canConfirm = rows.length > 0 && validation !== null && !dirty && validation.summary.errors === 0 && !submitting;

  async function handleConfirm() {
    if (!canConfirm) return;
    setSubmitting(true);
    setSubmitError(null);
    setServerRowErrors({});
    try {
      const { rows: payloadRows } = toBulkCreatePayload(rows);
      const result = await bulkCreatePMSchedules(payloadRows);
      onCreated?.(result.data);
    } catch (error) {
      if (Array.isArray(error.detail)) {
        const rowErrors = {};
        for (const entry of error.detail) {
          if (entry && typeof entry === "object" && entry.client_row_id) {
            rowErrors[entry.client_row_id] = entry.msg || "Rejected by the server.";
          }
        }
        setServerRowErrors(rowErrors);
      }
      setSubmitError(error.message);
      setDirty(true);
    } finally {
      setSubmitting(false);
    }
  }

  const rowActivityEditorRow = rows.find((r) => r.id === rowActivityEditorId) || null;

  return (
    <div data-testid="bulk-pm-schedule-editor">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md }}>
        <div>
          <h1 style={{ margin: 0, color: colors.text }}>Bulk PM Schedule</h1>
          <p style={{ margin: 0, color: colors.textMuted, fontSize: 12 }}>
            For the best experience editing many rows, use a desktop browser.
          </p>
        </div>
        <Button type="button" onClick={onClose}>
          Back to PM Schedules
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
            Apply to {selectedRows.length} selected row{selectedRows.length === 1 ? "" : "s"} (blank fields are left unchanged):
          </div>
          <div style={{ display: "flex", gap: spacing.xs, flexWrap: "wrap", alignItems: "center" }}>
            <select
              aria-label="Apply Frequency"
              style={inputStyle}
              value={applyForm.frequency}
              onChange={(e) => setApplyForm((f) => ({ ...f, frequency: e.target.value }))}
            >
              {APPLY_FREQUENCY_OPTIONS.map((o) => (
                <option key={o.value || "none"} value={o.value}>
                  {o.value ? o.label : "Frequency: no change"}
                </option>
              ))}
            </select>
            <input
              aria-label="Apply Start Date"
              type="date"
              style={inputStyle}
              value={applyForm.startDate}
              onChange={(e) => setApplyForm((f) => ({ ...f, startDate: e.target.value }))}
            />
            <input
              aria-label="Apply Assigned Technician"
              placeholder="Technician: no change"
              style={inputStyle}
              value={applyForm.technician}
              onChange={(e) => setApplyForm((f) => ({ ...f, technician: e.target.value }))}
            />
            <input
              aria-label="Apply Duration"
              type="number"
              min="0"
              step="0.25"
              placeholder="Duration: no change"
              style={inputStyle}
              value={applyForm.duration}
              onChange={(e) => setApplyForm((f) => ({ ...f, duration: e.target.value }))}
            />
            <input
              aria-label="Apply Notes"
              placeholder="Notes: no change"
              style={inputStyle}
              value={applyForm.notes}
              onChange={(e) => setApplyForm((f) => ({ ...f, notes: e.target.value }))}
            />
            <Button type="button" onClick={applyToSelected}>
              Apply to Selected
            </Button>
            <Button
              type="button"
              onClick={() => {
                setApplyActivitiesMap({});
                setApplyActivitiesOpen(true);
              }}
            >
              Apply Activities to Selected...
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
                <th style={thStyle}>Frequency *</th>
                <th style={thStyle}>Start Date *</th>
                <th style={thStyle}>Planned Activities</th>
                <th style={thStyle}>Assigned Technician</th>
                <th style={thStyle}>Duration</th>
                <th style={thStyle}>Notes</th>
                <th style={thStyle}>Validation</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const result = validation?.results[row.id];
                const serverError = serverRowErrors[row.id];
                return (
                  <tr key={row.id} data-testid={`bulk-row-${row.id}`}>
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
                          id={`bulk-pump-${row.id}`}
                          label="Pump"
                          assets={pumps.map((p) => ({ tag: p.tag, name: p.name }))}
                          selectedTag={row.pumpTag || null}
                          onSelect={(tag) => updateRowField(row.id, "pumpTag", tag || "")}
                        />
                      )}
                    </td>
                    <td style={tdStyle}>
                      <select
                        aria-label={`Frequency for row ${row.id}`}
                        style={inputStyle}
                        value={row.frequency}
                        onChange={(e) => updateRowField(row.id, "frequency", e.target.value)}
                      >
                        {SUPPORTED_FREQUENCIES.map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Start Date for row ${row.id}`}
                        type="date"
                        style={inputStyle}
                        value={row.startDate}
                        onChange={(e) => updateRowField(row.id, "startDate", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <ActivitiesCell plannedMap={row.plannedMap} onEdit={() => setRowActivityEditorId(row.id)} />
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Assigned Technician for row ${row.id}`}
                        style={inputStyle}
                        value={row.technician}
                        onChange={(e) => updateRowField(row.id, "technician", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Duration for row ${row.id}`}
                        type="number"
                        min="0"
                        step="0.25"
                        style={inputStyle}
                        value={row.duration}
                        onChange={(e) => updateRowField(row.id, "duration", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <input
                        aria-label={`Notes for row ${row.id}`}
                        style={inputStyle}
                        value={row.notes}
                        onChange={(e) => updateRowField(row.id, "notes", e.target.value)}
                      />
                    </td>
                    <td style={tdStyle}>
                      <StatusBadge level={result?.level} />
                      {result?.errors.map((message, i) => (
                        <p key={`err-${i}`} style={errorTextStyle}>
                          {message}
                        </p>
                      ))}
                      {result?.warnings.map((message, i) => (
                        <p key={`warn-${i}`} style={warningTextStyle}>
                          {message}
                        </p>
                      ))}
                      {serverError ? <p style={errorTextStyle}>{serverError}</p> : null}
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
            <span data-testid="bulk-validation-summary">
              Rows: {validation.summary.rows} · Ready: {validation.summary.ready} · Warnings: {validation.summary.warnings} · Errors:{" "}
              {validation.summary.errors}
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

      {rowActivityEditorRow ? (
        <ActivityEditorModal
          title={`Planned Activities -- ${rowActivityEditorRow.pumpTag || "row"}`}
          plannedMap={rowActivityEditorRow.plannedMap}
          onToggle={(code) => toggleRowActivity(rowActivityEditorRow.id, code)}
          onClose={() => setRowActivityEditorId(null)}
        />
      ) : null}

      {applyActivitiesOpen ? (
        <ActivityEditorModal
          title={`Apply Activities to ${selectedRows.length} Selected Row${selectedRows.length === 1 ? "" : "s"}`}
          plannedMap={applyActivitiesMap}
          onToggle={(code) => setApplyActivitiesMap((current) => ({ ...current, [code]: !current[code] }))}
          onClose={() => setApplyActivitiesOpen(false)}
          onApply={applyActivitiesToSelected}
          applyLabel="Apply Activities"
        />
      ) : null}
    </div>
  );
}
