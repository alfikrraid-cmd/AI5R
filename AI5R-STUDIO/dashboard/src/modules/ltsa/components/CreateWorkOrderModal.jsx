import { useState } from "react";
import { Button, Modal } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const WORK_TYPE_OPTIONS = ["CM", "PM", "INSPECTION"];
const PRIORITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

const EMPTY_FORM = {
  title: "",
  equipmentTag: "",
  area: "",
  workType: "CM",
  priority: "MEDIUM",
  assignedTechnician: "",
  dueDate: "",
  description: "",
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

export default function CreateWorkOrderModal({ isOpen, onClose, onCreate }) {
  const [form, setForm] = useState(EMPTY_FORM);

  function setField(name) {
    return (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (!form.title.trim()) {
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
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Work Order">
      <form onSubmit={handleSubmit}>
        <Field id="wo-title" label="Title">
          <input id="wo-title" style={fieldStyle} value={form.title} onChange={setField("title")} required />
        </Field>

        <Field id="wo-equipment-tag" label="Equipment Tag">
          <input
            id="wo-equipment-tag"
            style={fieldStyle}
            value={form.equipmentTag}
            onChange={setField("equipmentTag")}
          />
        </Field>

        <Field id="wo-area" label="Area">
          <input id="wo-area" style={fieldStyle} value={form.area} onChange={setField("area")} />
        </Field>

        <Field id="wo-work-type" label="Work Type">
          <select id="wo-work-type" style={fieldStyle} value={form.workType} onChange={setField("workType")}>
            {WORK_TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field id="wo-priority" label="Priority">
          <select id="wo-priority" style={fieldStyle} value={form.priority} onChange={setField("priority")}>
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field id="wo-assigned-technician" label="Assigned Technician">
          <input
            id="wo-assigned-technician"
            style={fieldStyle}
            value={form.assignedTechnician}
            onChange={setField("assignedTechnician")}
          />
        </Field>

        <Field id="wo-due-date" label="Due Date">
          <input
            id="wo-due-date"
            type="date"
            style={fieldStyle}
            value={form.dueDate}
            onChange={setField("dueDate")}
          />
        </Field>

        <Field id="wo-description" label="Description">
          <textarea
            id="wo-description"
            style={{ ...fieldStyle, minHeight: 72, resize: "vertical" }}
            value={form.description}
            onChange={setField("description")}
          />
        </Field>

        <div style={{ display: "flex", gap: spacing.sm, justifyContent: "flex-end" }}>
          <Button type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit">Create Work Order</Button>
        </div>
      </form>
    </Modal>
  );
}
