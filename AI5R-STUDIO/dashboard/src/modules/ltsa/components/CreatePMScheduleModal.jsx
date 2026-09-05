import { useEffect, useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { nextMonthFirstDay } from "../utils/pmMapping";
import PMActivityFamilyChecklist from "./PMActivityFamilyChecklist";
import { buildPlannedActivitiesPayload } from "../utils/pmActivityCatalog";

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

// AI5R-PHASE4E1 -- OWNER DECISIONS 1-5: Schedule Code is now system-
// generated (never typed by a human, so it has no field here at all) and
// Procedure is no longer a required user-facing field (replaced by an
// optional "Notes" field, mapped onto the same existing `procedure`
// column by PM.jsx's handleCreate -- see that file for the mapping).
//
// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "Normal operational UI should
// create schedules for NEXT MONTH... Derive next calendar month from
// current operational date." A function, not a static value, so the
// default is computed fresh each time the modal opens (see
// initialFormFor's own useEffect below) rather than frozen at module load.
function emptyForm() {
  return {
    notes: "",
    equipmentTag: "",
    frequency: "MONTHLY",
    triggerType: "CALENDAR",
    assignedTechnician: "",
    startDate: nextMonthFirstDay(),
    estimatedDurationHours: "",
  };
}

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

// MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- initialEquipmentTag is optional
// and additive: every existing caller that omits it keeps the exact same
// blank-equipment behavior as before. Used by PM.jsx's "No active PM
// Schedule is available for this pump" flow to prefill the pump that was
// already being viewed, rather than requiring it to be retyped.
function initialFormFor(initialEquipmentTag) {
  return initialEquipmentTag ? { ...emptyForm(), equipmentTag: initialEquipmentTag } : emptyForm();
}

export default function CreatePMScheduleModal({ isOpen, onClose, onCreate, initialEquipmentTag = "" }) {
  const [form, setForm] = useState(() => initialFormFor(initialEquipmentTag));
  // AI5R-PHASE4E1, OWNER DECISION 6/7: PLANNED activities only -- this map
  // never feeds pm_occurrence.activities (PERFORMED activities) and is
  // reset independently of it; PMActivityFamilyChecklist itself carries no
  // "performed" semantics, so reusing it here for planning is safe.
  const [plannedMap, setPlannedMap] = useState({});

  useEffect(() => {
    if (isOpen) {
      setForm(initialFormFor(initialEquipmentTag));
      setPlannedMap({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialEquipmentTag]);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function togglePlanned(code) {
    setPlannedMap((current) => ({ ...current, [code]: !current[code] }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.equipmentTag.trim()) {
      return;
    }

    const plannedActivities = buildPlannedActivitiesPayload(plannedMap);
    onCreate({
      equipmentTag: form.equipmentTag,
      frequency: form.frequency,
      triggerType: form.triggerType,
      assignedTechnician: form.assignedTechnician,
      startDate: form.startDate,
      estimatedDurationHours: form.estimatedDurationHours === "" ? 0 : Number(form.estimatedDurationHours),
      notes: form.notes,
      plannedActivities: plannedActivities.length > 0 ? plannedActivities : null,
    });
    setForm(emptyForm());
    setPlannedMap({});
  }

  function handleClose() {
    setForm(emptyForm());
    setPlannedMap({});
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create PM Schedule">
      <form onSubmit={handleSubmit}>
        <Field id="pm-equipment" label="Equipment">
          <input
            id="pm-equipment"
            style={fieldStyle}
            value={form.equipmentTag}
            onChange={setField("equipmentTag")}
            required
          />
        </Field>

        <Field id="pm-frequency" label="Frequency">
          <select id="pm-frequency" style={fieldStyle} value={form.frequency} onChange={setField("frequency")}>
            {FREQUENCY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="pm-trigger-type" label="Trigger Type">
          <select
            id="pm-trigger-type"
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

        <Field id="pm-start-date" label="Start Date">
          <input
            id="pm-start-date"
            type="date"
            style={fieldStyle}
            value={form.startDate}
            onChange={setField("startDate")}
          />
        </Field>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={labelStyle}>Planned Activities</div>
          <PMActivityFamilyChecklist doneMap={plannedMap} onToggle={togglePlanned} />
        </div>

        <Field id="pm-technician" label="Technician">
          <input
            id="pm-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
        </Field>

        <Field id="pm-estimated-duration" label="Estimated Duration">
          <input
            id="pm-estimated-duration"
            type="number"
            min="0"
            step="0.25"
            style={fieldStyle}
            value={form.estimatedDurationHours}
            onChange={setField("estimatedDurationHours")}
          />
        </Field>

        <Field id="pm-notes" label="Notes">
          <input id="pm-notes" style={fieldStyle} value={form.notes} onChange={setField("notes")} />
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Create PM Schedule</Button>
        </div>
      </form>
    </Modal>
  );
}
