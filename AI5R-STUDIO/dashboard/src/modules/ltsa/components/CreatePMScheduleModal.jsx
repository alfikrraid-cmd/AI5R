import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

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

const CHECKLIST_TEMPLATES = {
  "Standard Lubrication Checklist": [
    "Check oil level and condition",
    "Grease bearing housings",
    "Record vibration baseline reading",
  ],
  "Vibration & Alignment Checklist": [
    "Record vibration baseline reading",
    "Inspect coupling alignment",
    "Check foundation bolts",
  ],
  "Seal Inspection Checklist": [
    "Inspect seal chamber for leakage",
    "Check seal flush pressure",
    "Record vibration and temperature readings",
  ],
  "Operator Walkdown Checklist": [
    "Check for visible leaks",
    "Listen for abnormal noise",
    "Verify local gauge readings",
  ],
};

const CHECKLIST_TEMPLATE_NAMES = Object.keys(CHECKLIST_TEMPLATES);

const EMPTY_FORM = {
  equipmentTag: "",
  frequency: "MONTHLY",
  triggerType: "CALENDAR",
  assignedTechnician: "",
  startDate: "",
  estimatedDurationHours: "",
  checklistTemplate: CHECKLIST_TEMPLATE_NAMES[0],
};

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

export default function CreatePMScheduleModal({ isOpen, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY_FORM);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.equipmentTag.trim()) {
      return;
    }

    onCreate({
      equipmentTag: form.equipmentTag,
      frequency: form.frequency,
      triggerType: form.triggerType,
      assignedTechnician: form.assignedTechnician,
      startDate: form.startDate,
      estimatedDurationHours: form.estimatedDurationHours === "" ? 0 : Number(form.estimatedDurationHours),
      checklistTemplate: form.checklistTemplate,
      checklist: CHECKLIST_TEMPLATES[form.checklistTemplate],
    });
    setForm(EMPTY_FORM);
  }

  function handleClose() {
    setForm(EMPTY_FORM);
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

        <Field id="pm-technician" label="Technician">
          <input
            id="pm-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
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

        <Field id="pm-checklist-template" label="Checklist Template">
          <select
            id="pm-checklist-template"
            style={fieldStyle}
            value={form.checklistTemplate}
            onChange={setField("checklistTemplate")}
          >
            {CHECKLIST_TEMPLATE_NAMES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Save</Button>
        </div>
      </form>
    </Modal>
  );
}
