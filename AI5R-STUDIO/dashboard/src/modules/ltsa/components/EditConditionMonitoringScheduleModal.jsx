import { useEffect, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- Edit Schedule for an EXISTING
// condition_monitoring_schedule row, using the already-real PATCH
// /api/ltsa/condition-monitoring-schedules/{code} endpoint
// (updateConditionMonitoringSchedule, ai5rClient.js) and its exact field
// set (ConditionMonitoringScheduleUpdateRequest: monitoring_type,
// measurement_point, frequency, interval_unit, effective_date). Schedule
// Code and Equipment are immutable identity -- shown read-only, never sent
// in the PATCH body (the backend model has no field for either).
//
// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- nextDue/status added
// (migration 029), mirroring EditPMScheduleModal.jsx's own next_due/
// status fields exactly. PLANNED/ACTIVE/OVERDUE are computed display
// values (conditionMonitoringMapping.js's own computeDisplayStatus),
// never legitimate to write back -- only the real stored values
// (PLANNED/ACTIVE/COMPLETED/CANCELLED) are offered here, giving
// "authorized cancellation" a real UI path through this same PATCH
// endpoint.

const STATUS_OPTIONS = [
  { value: "PLANNED", label: "Planned" },
  { value: "ACTIVE", label: "Active" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELLED", label: "Cancelled" },
];

const fieldStyle = {
  width: "100%",
  background: colors.panel,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: 4,
  padding: "6px 8px",
  boxSizing: "border-box",
};
const readOnlyFieldStyle = { ...fieldStyle, color: colors.textMuted, background: "transparent" };
const labelStyle = { display: "block", color: colors.textMuted, fontSize: 12, marginBottom: 4 };

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

function formFromSchedule(schedule) {
  return {
    monitoringType: schedule?.monitoringType ?? "",
    measurementPoint: schedule?.measurementPoint ?? "",
    frequency: schedule?.frequency ?? "",
    intervalUnit: schedule?.intervalUnit ?? "",
    effectiveDate: schedule?.effectiveDate ?? "",
    nextDue: schedule?.nextDue ?? "",
    status: schedule?.rawStatus ?? "PLANNED",
  };
}

export default function EditConditionMonitoringScheduleModal({ isOpen, onClose, onSave, schedule }) {
  const [form, setForm] = useState(() => formFromSchedule(schedule));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setForm(formFromSchedule(schedule));
      setError(null);
    }
  }, [isOpen, schedule]);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(schedule.id, {
        monitoring_type: form.monitoringType,
        measurement_point: form.measurementPoint || null,
        frequency: form.frequency || null,
        interval_unit: form.intervalUnit || null,
        effective_date: form.effectiveDate || null,
        next_due: form.nextDue || null,
        status: form.status,
      });
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!schedule) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Edit Condition Monitoring Schedule — ${schedule.id}`}>
      <form onSubmit={handleSubmit}>
        <Field id="edit-cmon-schedule-code" label="Schedule Code">
          <input id="edit-cmon-schedule-code" style={readOnlyFieldStyle} value={schedule.id} readOnly disabled />
        </Field>
        <Field id="edit-cmon-equipment" label="Equipment">
          <input id="edit-cmon-equipment" style={readOnlyFieldStyle} value={schedule.equipmentTag ?? ""} readOnly disabled />
        </Field>

        <Field id="edit-cmon-monitoring-type" label="Monitoring Type">
          <input
            id="edit-cmon-monitoring-type"
            style={fieldStyle}
            value={form.monitoringType}
            onChange={setField("monitoringType")}
            required
          />
        </Field>

        <Field id="edit-cmon-measurement-point" label="Measurement Point">
          <input
            id="edit-cmon-measurement-point"
            style={fieldStyle}
            value={form.measurementPoint}
            onChange={setField("measurementPoint")}
          />
        </Field>

        <Field id="edit-cmon-frequency" label="Frequency">
          <input id="edit-cmon-frequency" style={fieldStyle} value={form.frequency} onChange={setField("frequency")} />
        </Field>

        <Field id="edit-cmon-interval-unit" label="Interval Unit">
          <input id="edit-cmon-interval-unit" style={fieldStyle} value={form.intervalUnit} onChange={setField("intervalUnit")} />
        </Field>

        <Field id="edit-cmon-effective-date" label="Effective Date">
          <input
            id="edit-cmon-effective-date"
            type="date"
            style={fieldStyle}
            value={form.effectiveDate}
            onChange={setField("effectiveDate")}
          />
        </Field>

        <Field id="edit-cmon-next-due" label="Next Due">
          <input
            id="edit-cmon-next-due"
            type="date"
            style={fieldStyle}
            value={form.nextDue}
            onChange={setField("nextDue")}
          />
        </Field>

        <Field id="edit-cmon-status" label="Status">
          <select id="edit-cmon-status" style={fieldStyle} value={form.status} onChange={setField("status")}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        {error && (
          <p role="alert" style={{ color: colors.danger, fontSize: 13 }} data-testid="edit-cmon-schedule-error">
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
