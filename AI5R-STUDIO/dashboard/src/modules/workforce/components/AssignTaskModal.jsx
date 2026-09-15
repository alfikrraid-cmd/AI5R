import { useEffect, useState } from "react";
import Modal from "../../../design-system/components/Modal";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";
import { assignWorkforceTask } from "../../../api/workforceClient";

const VALID_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function AssignTaskModal({
  isOpen,
  onClose,
  employees = [],
  preselectedEmployee = null,
  onTaskAssigned,
}) {
  const [employeeId, setEmployeeId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [isProduction, setIsProduction] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      if (preselectedEmployee?.employee_id) {
        setEmployeeId(preselectedEmployee.employee_id);
      } else if (employees.length > 0) {
        setEmployeeId(employees[0].employee_id);
      } else {
        setEmployeeId("");
      }
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
      setIsProduction(false);
      setError(null);
      setSubmitting(false);
    }
  }, [isOpen, preselectedEmployee, employees]);

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e?.preventDefault?.();
    if (submitting) return;

    setError(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Task title is required");
      return;
    }

    if (!employeeId) {
      setError("Please select an employee");
      return;
    }

    const selectedEmp = employees.find((emp) => emp.employee_id === employeeId);
    if (!selectedEmp) {
      setError(`Selected employee not found: ${employeeId}`);
      return;
    }

    if (!VALID_PRIORITIES.includes(priority)) {
      setError(`Invalid priority: ${priority}`);
      return;
    }

    setSubmitting(true);
    try {
      const result = await assignWorkforceTask({
        title: trimmedTitle,
        description: description.trim(),
        positionId: selectedEmp.position_id,
        employeeId: selectedEmp.employee_id,
        isProduction,
        metadata: {
          priority,
          assigned_by: "CHIEF",
        },
      });

      onTaskAssigned?.(result);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to assign task");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Assign Work Item">
      <form
        data-testid="assign-task-form"
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: spacing.md }}
      >
        {error ? (
          <div
            data-testid="assign-task-error"
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${colors.danger}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              color: colors.danger,
              fontSize: typography.size.sm,
            }}
          >
            {error}
          </div>
        ) : null}

        {/* Employee Select */}
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs / 2 }}>
          <label
            htmlFor="assign-employee-select"
            style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted }}
          >
            ASSIGN TO EMPLOYEE (CANONICAL IDENTITY)
          </label>
          <select
            id="assign-employee-select"
            data-testid="assign-employee-select"
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            disabled={submitting}
            style={{
              background: colors.background,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              fontSize: typography.size.sm,
            }}
          >
            {employees.map((emp) => (
              <option key={emp.employee_id} value={emp.employee_id}>
                {emp.employee_name} — {emp.position_id} ({emp.employee_id})
              </option>
            ))}
          </select>
        </div>

        {/* Task Title */}
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs / 2 }}>
          <label
            htmlFor="assign-task-title"
            style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted }}
          >
            TASK TITLE *
          </label>
          <input
            id="assign-task-title"
            data-testid="assign-task-title-input"
            type="text"
            placeholder="e.g. Implement condition monitoring export worker"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={submitting}
            style={{
              background: colors.background,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              fontSize: typography.size.sm,
            }}
          />
        </div>

        {/* Task Description */}
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs / 2 }}>
          <label
            htmlFor="assign-task-description"
            style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted }}
          >
            WORK DESCRIPTION
          </label>
          <textarea
            id="assign-task-description"
            data-testid="assign-task-desc-input"
            rows={3}
            placeholder="Describe the objective, constraints, and acceptance criteria..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={submitting}
            style={{
              background: colors.background,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              fontSize: typography.size.sm,
              resize: "vertical",
            }}
          />
        </div>

        {/* Priority */}
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs / 2 }}>
          <label
            htmlFor="assign-task-priority"
            style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted }}
          >
            PRIORITY
          </label>
          <select
            id="assign-task-priority"
            data-testid="assign-task-priority-select"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            disabled={submitting}
            style={{
              background: colors.background,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              fontSize: typography.size.sm,
            }}
          >
            {VALID_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {/* Production Impact Checkbox */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: spacing.sm,
            background: colors.background,
            padding: spacing.sm,
            borderRadius: spacing.xs,
            border: `1px solid ${isProduction ? colors.warning : colors.border}`,
          }}
        >
          <input
            id="assign-is-production"
            data-testid="assign-task-production-checkbox"
            type="checkbox"
            checked={isProduction}
            onChange={(e) => setIsProduction(e.target.checked)}
            disabled={submitting}
            style={{ marginTop: 3 }}
          />
          <div>
            <label
              htmlFor="assign-is-production"
              style={{
                fontSize: typography.size.sm,
                fontWeight: typography.weight.bold,
                color: isProduction ? colors.warning : colors.text,
                cursor: "pointer",
              }}
            >
              Production Release Impact
            </label>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: 2 }}>
              When enabled, this task will be gated and require explicit Human Chief Authorization before release.
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: spacing.sm, marginTop: spacing.sm }}>
          <button
            type="button"
            data-testid="assign-task-cancel-button"
            onClick={onClose}
            disabled={submitting}
            style={{
              background: "transparent",
              color: colors.textMuted,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            data-testid="assign-task-submit-button"
            disabled={submitting}
            style={{
              background: submitting ? colors.textMuted : colors.info,
              color: colors.text,
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Assigning Task..." : "Create & Assign Task"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
