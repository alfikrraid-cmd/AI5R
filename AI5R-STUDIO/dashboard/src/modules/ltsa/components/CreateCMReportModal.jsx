import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const FAILURE_CATEGORY_OPTIONS = [
  { value: "MECHANICAL", label: "Mechanical" },
  { value: "ELECTRICAL", label: "Electrical" },
  { value: "SEAL_FAILURE", label: "Seal Failure" },
  { value: "INSTRUMENTATION", label: "Instrumentation" },
  { value: "PROCESS", label: "Process" },
];

const SEVERITY_OPTIONS = ["MINOR", "MODERATE", "MAJOR", "CRITICAL"];
const PRIORITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

const EMPTY_FORM = {
  equipmentTag: "",
  failureCategory: "MECHANICAL",
  severity: "MODERATE",
  priority: "MEDIUM",
  failureDescription: "",
  immediateAction: "",
  assignedTechnician: "",
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

export default function CreateCMReportModal({ isOpen, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY_FORM);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.equipmentTag.trim() || !form.failureDescription.trim()) {
      return;
    }

    onCreate(form);
    setForm(EMPTY_FORM);
  }

  function handleClose() {
    setForm(EMPTY_FORM);
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Corrective Maintenance Report">
      <form onSubmit={handleSubmit}>
        <Field id="cm-equipment" label="Equipment">
          <input
            id="cm-equipment"
            style={fieldStyle}
            value={form.equipmentTag}
            onChange={setField("equipmentTag")}
            required
          />
        </Field>

        <Field id="cm-failure-category" label="Failure Category">
          <select
            id="cm-failure-category"
            style={fieldStyle}
            value={form.failureCategory}
            onChange={setField("failureCategory")}
          >
            {FAILURE_CATEGORY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="cm-severity" label="Severity">
          <select id="cm-severity" style={fieldStyle} value={form.severity} onChange={setField("severity")}>
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field id="cm-priority" label="Priority">
          <select id="cm-priority" style={fieldStyle} value={form.priority} onChange={setField("priority")}>
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field id="cm-failure-description" label="Failure Description">
          <textarea
            id="cm-failure-description"
            style={{ ...fieldStyle, minHeight: 72, resize: "vertical" }}
            value={form.failureDescription}
            onChange={setField("failureDescription")}
            required
          />
        </Field>

        <Field id="cm-immediate-action" label="Immediate Action">
          <textarea
            id="cm-immediate-action"
            style={{ ...fieldStyle, minHeight: 56, resize: "vertical" }}
            value={form.immediateAction}
            onChange={setField("immediateAction")}
          />
        </Field>

        <Field id="cm-assigned-technician" label="Assigned Technician">
          <input
            id="cm-assigned-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
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
