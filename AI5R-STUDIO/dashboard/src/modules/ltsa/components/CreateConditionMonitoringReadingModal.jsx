import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  MEASUREMENT_PAIR_FIELDS,
  MEASUREMENT_SINGLE_FIELDS,
  LEAK_FIELD,
  emptyMeasurementFormValues,
  buildMeasurementsPayload,
} from "../utils/conditionMonitoringMeasurementFields";

const OPERATING_STATE_OPTIONS = ["Running", "Standby", "Repair"];

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

const LEAK_OPTIONS = [
  { value: "", label: "Not Recorded" },
  { value: "false", label: "No Leak" },
  { value: "true", label: "Leak Detected" },
];

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

        <Field id="cmon-operating-state" label="Pump Operating State">
          <select
            id="cmon-operating-state"
            style={fieldStyle}
            value={measurements.pumpOperatingState}
            onChange={setMeasurementField("pumpOperatingState")}
          >
            <option value="">Not Recorded</option>
            {OPERATING_STATE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        {/* MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- every canonical
            DE/NDE measurement pair (golden-evidence-established, migration
            014's own header), rendered from the one shared field list so
            this form and the Edit panel never diverge. DE/NDE are always
            two separate inputs -- never collapsed into one. */}
        {MEASUREMENT_PAIR_FIELDS.map((field) => (
          <div key={field.group} style={{ marginBottom: spacing.sm }}>
            <div style={labelStyle}>
              {field.group} ({field.unit})
            </div>
            <div style={{ display: "flex", gap: spacing.sm }}>
              {/* Label text includes the group name (e.g. "Bearing Temp
                  DE") -- a bare "DE"/"NDE" would be ambiguous across the
                  many measurement groups on this one form. */}
              <Field id={`cmon-${field.deKey}`} label={`${field.group} DE`}>
                <input
                  id={`cmon-${field.deKey}`}
                  type="number"
                  step="any"
                  style={fieldStyle}
                  value={measurements[field.deKey]}
                  onChange={setMeasurementField(field.deKey)}
                />
              </Field>
              <Field id={`cmon-${field.ndeKey}`} label={`${field.group} NDE`}>
                <input
                  id={`cmon-${field.ndeKey}`}
                  type="number"
                  step="any"
                  style={fieldStyle}
                  value={measurements[field.ndeKey]}
                  onChange={setMeasurementField(field.ndeKey)}
                />
              </Field>
            </div>
          </div>
        ))}

        {MEASUREMENT_SINGLE_FIELDS.map((field) => (
          <Field key={field.key} id={`cmon-${field.key}`} label={`${field.label} (${field.unit})`}>
            <input
              id={`cmon-${field.key}`}
              type="number"
              step="any"
              style={fieldStyle}
              value={measurements[field.key]}
              onChange={setMeasurementField(field.key)}
            />
          </Field>
        ))}

        {/* Leakage: tri-state, never inferred. A blank selection persists
            as NULL (not recorded), never as "no leak". */}
        <div style={{ marginBottom: spacing.sm }}>
          <div style={labelStyle}>{LEAK_FIELD.group}</div>
          <div style={{ display: "flex", gap: spacing.sm }}>
            <Field id={`cmon-${LEAK_FIELD.deKey}`} label={`${LEAK_FIELD.group} DE`}>
              <select
                id={`cmon-${LEAK_FIELD.deKey}`}
                style={fieldStyle}
                value={measurements[LEAK_FIELD.deKey]}
                onChange={setMeasurementField(LEAK_FIELD.deKey)}
              >
                {LEAK_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field id={`cmon-${LEAK_FIELD.ndeKey}`} label={`${LEAK_FIELD.group} NDE`}>
              <select
                id={`cmon-${LEAK_FIELD.ndeKey}`}
                style={fieldStyle}
                value={measurements[LEAK_FIELD.ndeKey]}
                onChange={setMeasurementField(LEAK_FIELD.ndeKey)}
              >
                {LEAK_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
        </div>

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
