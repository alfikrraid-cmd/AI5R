import { useEffect, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- Edit Schedule for an EXISTING
// pm_schedule row, using the already-real PATCH /api/ltsa/pm-schedules/{code}
// endpoint (updatePMSchedule, ai5rClient.js) and its exact field set
// (PMScheduleUpdateRequest: procedure, frequency, trigger_type,
// interval_unit, effective_date, next_due, assigned_to, status). Schedule
// Code and Equipment are immutable identity -- shown read-only, never sent
// in the PATCH body (the backend model has no field for either). Prefilled
// from the real `pm` record (mapPMScheduleRecord's rawStatus/intervalUnit/
// effectiveDate additions), never a blank/guessed default -- this is an
// edit of a real record, not a second create flow.
const FREQUENCY_OPTIONS = [
  { value: "DAILY", label: "Daily" },
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "RUNTIME_BASED", label: "Runtime-based" },
];

const TRIGGER_TYPE_OPTIONS = [
  { value: "CALENDAR", label: "Calendar" },
  { value: "METER", label: "Runtime Meter" },
];

// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- PLANNED/ACTIVE/OVERDUE are
// computed display values (pmMapping.js's own computeDisplayStatus), never
// legitimate to write back. ACTIVE/ON_HOLD/COMPLETED/CANCELLED are the
// real STORED values a user may set here -- COMPLETED/CANCELLED added so
// "authorized cancellation" (the mission's own alternative lifecycle
// branch) and a manual completion correction both have a real UI path
// through this same existing PATCH endpoint, no new endpoint required.
const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Active" },
  { value: "ON_HOLD", label: "On Hold" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELLED", label: "Cancelled" },
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

const readOnlyFieldStyle = { ...fieldStyle, color: colors.textMuted, background: "transparent" };
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

function formFromSchedule(pm) {
  return {
    procedure: pm?.procedure ?? "",
    frequency: pm?.frequency ?? "MONTHLY",
    triggerType: pm?.triggerType ?? "CALENDAR",
    intervalUnit: pm?.intervalUnit ?? "",
    effectiveDate: pm?.effectiveDate ?? "",
    nextDue: pm?.nextDue ?? "",
    assignedTechnician: pm?.assignedTechnician ?? "",
    status: pm?.rawStatus ?? "ACTIVE",
  };
}

export default function EditPMScheduleModal({ isOpen, onClose, onSave, pm }) {
  const [form, setForm] = useState(() => formFromSchedule(pm));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Re-prefill whenever a different schedule is opened for edit, or the
  // underlying record changes (e.g. reopened after a prior save).
  useEffect(() => {
    if (isOpen) {
      setForm(formFromSchedule(pm));
      setError(null);
    }
  }, [isOpen, pm]);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(pm.id, {
        procedure: form.procedure,
        frequency: form.frequency,
        trigger_type: form.triggerType,
        interval_unit: form.intervalUnit || null,
        effective_date: form.effectiveDate || null,
        next_due: form.nextDue || null,
        assigned_to: form.assignedTechnician || null,
        status: form.status,
      });
      onClose();
    } catch (err) {
      // Verbatim backend detail, never a generic "failed" message -- same
      // convention ConditionMonitoring.jsx's createError already uses.
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!pm) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Edit PM Schedule — ${pm.id}`}>
      <form onSubmit={handleSubmit}>
        <Field id="edit-pm-schedule-code" label="Schedule Code">
          <input id="edit-pm-schedule-code" style={readOnlyFieldStyle} value={pm.id} readOnly disabled />
        </Field>
        <Field id="edit-pm-equipment" label="Equipment">
          <input id="edit-pm-equipment" style={readOnlyFieldStyle} value={pm.equipmentTag ?? ""} readOnly disabled />
        </Field>

        <Field id="edit-pm-procedure" label="Procedure">
          <input
            id="edit-pm-procedure"
            style={fieldStyle}
            value={form.procedure}
            onChange={setField("procedure")}
            required
          />
        </Field>

        <Field id="edit-pm-frequency" label="Frequency">
          <select id="edit-pm-frequency" style={fieldStyle} value={form.frequency} onChange={setField("frequency")}>
            {FREQUENCY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="edit-pm-trigger-type" label="Trigger Type">
          <select
            id="edit-pm-trigger-type"
            style={fieldStyle}
            value={form.triggerType}
            onChange={setField("triggerType")}
          >
            {TRIGGER_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="edit-pm-interval-unit" label="Interval Unit">
          <input id="edit-pm-interval-unit" style={fieldStyle} value={form.intervalUnit} onChange={setField("intervalUnit")} />
        </Field>

        <Field id="edit-pm-effective-date" label="Effective Date">
          <input
            id="edit-pm-effective-date"
            type="date"
            style={fieldStyle}
            value={form.effectiveDate}
            onChange={setField("effectiveDate")}
          />
        </Field>

        <Field id="edit-pm-next-due" label="Next Due">
          <input
            id="edit-pm-next-due"
            type="date"
            style={fieldStyle}
            value={form.nextDue}
            onChange={setField("nextDue")}
          />
        </Field>

        <Field id="edit-pm-technician" label="Technician">
          <input
            id="edit-pm-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
        </Field>

        <Field id="edit-pm-status" label="Status">
          <select id="edit-pm-status" style={fieldStyle} value={form.status} onChange={setField("status")}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        {error && (
          <p role="alert" style={{ color: colors.danger, fontSize: 13 }} data-testid="edit-pm-schedule-error">
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
