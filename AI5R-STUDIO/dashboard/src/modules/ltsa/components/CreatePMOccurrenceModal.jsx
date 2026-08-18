import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-PM-CM-INTAKE-001 -- golden evidence (Laporan PM, CM &
// Pemasangan Seal, page 34/35): a fixed 33-item cleaning-accessories
// checklist. This form offers the most common items as checkboxes
// (matching the golden report's own most-frequently-recorded activities)
// rather than all 33 -- the backend's `activities` JSONB accepts any
// subset, so this is a UI scope choice, not a data-model limit; a
// technician who needs a less common item can still record it via
// remarks until a fuller checklist UI follows.
const ACTIVITY_OPTIONS = [
  { code: "1", description: "Flushing Line", side: null },
  { code: "4", description: "Quench Line", side: null },
  { code: "19", description: "Strainer", side: null },
  { code: "17", description: "Check Valve DE Side", side: "DE" },
  { code: "18", description: "Check Valve NDE Side", side: "NDE" },
  { code: "6", description: "Reservoir", side: null },
  { code: "8", description: "Cooling Water Cooler", side: null },
];

const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: spacing.xs,
  padding: `${spacing.xs}px ${spacing.sm}px`,
  boxSizing: "border-box",
};

const labelStyle = { display: "block", color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs };

function Field({ id, label, children }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      {children}
    </div>
  );
}

export default function CreatePMOccurrenceModal({ isOpen, onClose, onCreate, pmScheduleCode, equipmentTag }) {
  const [occurrenceDate, setOccurrenceDate] = useState("");
  const [doneActivities, setDoneActivities] = useState({});
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  function toggleActivity(code) {
    setDoneActivities((current) => ({ ...current, [code]: !current[code] }));
  }

  function resetForm() {
    setOccurrenceDate("");
    setDoneActivities({});
    setRemarks("");
    setError(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const activities = ACTIVITY_OPTIONS.map((option) => ({
        ...option,
        done: Boolean(doneActivities[option.code]),
      }));
      await onCreate({ occurrenceDate: occurrenceDate || null, activities, remarks: remarks || null });
      resetForm();
    } catch (err) {
      // Verbatim backend detail, never a generic "failed" message.
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Record PM Occurrence">
      <form onSubmit={handleSubmit} data-testid="pm-occurrence-form">
        {error && (
          <p className="confidence-label" style={{ color: "var(--color-danger, #d33)" }} data-testid="pm-occurrence-error">
            {error}
          </p>
        )}

        <p className="confidence-label">
          {equipmentTag} &middot; {pmScheduleCode}
        </p>

        <Field id="pm-occ-date" label="Occurrence Date">
          <input
            id="pm-occ-date"
            type="date"
            style={fieldStyle}
            value={occurrenceDate}
            onChange={(e) => setOccurrenceDate(e.target.value)}
          />
        </Field>

        <div style={{ marginBottom: spacing.sm }}>
          <div className="confidence-label" style={{ marginBottom: spacing.xs }}>Activities</div>
          {ACTIVITY_OPTIONS.map((option) => (
            <label key={option.code} style={{ display: "flex", alignItems: "center", gap: spacing.xs, color: colors.text }}>
              <input
                type="checkbox"
                checked={Boolean(doneActivities[option.code])}
                onChange={() => toggleActivity(option.code)}
              />
              {option.description}
            </label>
          ))}
        </div>

        <Field id="pm-occ-remarks" label="Remarks">
          <textarea
            id="pm-occ-remarks"
            style={{ ...fieldStyle, minHeight: 60 }}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save Draft"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
