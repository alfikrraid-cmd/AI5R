import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import spacing from "../../../design-system/theme/spacing";
import { emptyMeasurementFormValues, buildMeasurementsPayload } from "../utils/conditionMonitoringMeasurementFields";
import ConditionMonitoringMeasurementFieldsForm, { fieldStyle, labelStyle, Field } from "./ConditionMonitoringMeasurementFieldsForm";

/**
 * MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- real persistence: this
 * form's `onCreate` payload feeds ConditionMonitoring.jsx's
 * handleCreateReading, which calls the real createConditionMonitoringReading
 * API (built by MWO-LTSA-PM-CM-INTAKE-001; wired real since that MWO --
 * this header previously said "client-state-only", which was already
 * stale before this closure MWO touched the file). `measurements` is
 * built once here via the shared buildMeasurementsPayload() (conditionMonitoring
 * MeasurementFields.js), the same helper the Edit panel uses, so Create
 * and Edit can never diverge on null-coercion/DE-NDE/leak-tri-state rules.
 */
export default function CreateConditionMonitoringReadingModal({ isOpen, onClose, onCreate, schedules }) {
  const [scheduleCode, setScheduleCode] = useState("");
  const [readingDate, setReadingDate] = useState("");
  const [measurements, setMeasurements] = useState(emptyMeasurementFormValues());

  function setMeasurementField(name) {
    return (event) => setMeasurements((current) => ({ ...current, [name]: event.target.value }));
  }

  function resetForm() {
    setScheduleCode("");
    setReadingDate("");
    setMeasurements(emptyMeasurementFormValues());
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!scheduleCode) {
      return;
    }

    const schedule = schedules.find((candidate) => candidate.id === scheduleCode);

    onCreate({
      scheduleCode,
      equipmentTag: schedule?.equipmentTag ?? null,
      readingDate,
      measurements: buildMeasurementsPayload(measurements),
    });
    resetForm();
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Condition Monitoring Reading">
      <form onSubmit={handleSubmit}>
        <Field id="cmon-schedule" label="Schedule">
          <select
            id="cmon-schedule"
            style={fieldStyle}
            value={scheduleCode}
            onChange={(event) => setScheduleCode(event.target.value)}
            required
          >
            <option value="">Select a schedule...</option>
            {schedules.map((schedule) => (
              <option key={schedule.id} value={schedule.id}>
                {schedule.id} — {schedule.equipmentTag}
              </option>
            ))}
          </select>
        </Field>

        <Field id="cmon-reading-date" label="Reading Date">
          <input
            id="cmon-reading-date"
            type="date"
            style={fieldStyle}
            value={readingDate}
            onChange={(event) => setReadingDate(event.target.value)}
          />
        </Field>

        <ConditionMonitoringMeasurementFieldsForm measurements={measurements} onFieldChange={setMeasurementField} idPrefix="cmon" />

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Create Reading</Button>
        </div>
      </form>
    </Modal>
  );
}
