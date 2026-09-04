import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { buildActivitiesPayload } from "../utils/pmActivityCatalog";
import PMActivityFamilyChecklist from "./PMActivityFamilyChecklist";

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
      const activities = buildActivitiesPayload(doneActivities);
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
          <PMActivityFamilyChecklist doneMap={doneActivities} onToggle={toggleActivity} />
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
