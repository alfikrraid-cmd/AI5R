import Badge from "../../../design-system/components/Badge";
import Modal from "../../../design-system/components/Modal";
import ProgressBar from "../../../design-system/components/ProgressBar";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function EmployeeDetailModal({ isOpen, onClose, employee }) {
  if (!employee) return null;

  const skills = employee.skills || [];
  const cognitiveFunctions = employee.cognitive_functions || [];
  const activities = employee.activities || [];
  const currentTask = employee.current_task;
  const progress = employee.task_progress ?? 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${employee.employee_name} — Profile`}
    >
      <div data-testid="employee-detail-content" style={{ display: "flex", flexDirection: "column", gap: spacing.md }}>
        {/* Identity Section */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: typography.size.sm, fontWeight: typography.weight.bold, color: colors.text }}>
              {employee.role || employee.title}
            </div>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
              Position: <code>{employee.position_id}</code> | ID: <code>{employee.employee_id}</code>
            </div>
          </div>
          <Badge variant={employee.status === "AVAILABLE" ? "success" : employee.status === "WORKING" ? "purple" : "warning"}>
            {employee.status}
          </Badge>
        </div>

        {/* Current Assignment */}
        <div style={{ background: colors.background, padding: spacing.sm, borderRadius: spacing.xs }}>
          <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, textTransform: "uppercase", marginBottom: spacing.xs }}>
            Active Task
          </div>
          {currentTask ? (
            <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
              <div style={{ fontWeight: typography.weight.bold, color: colors.text }}>
                {currentTask.title}
              </div>
              {currentTask.description ? (
                <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                  {currentTask.description}
                </div>
              ) : null}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: typography.size.xs, color: colors.textMuted }}>
                <span>Status: {currentTask.status}</span>
                <span>{progress}%</span>
              </div>
              <ProgressBar value={progress} max={100} />
            </div>
          ) : (
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
              No active task assigned. Ready for delegation.
            </div>
          )}
        </div>

        {/* Skills & Cognitive Functions */}
        <div>
          <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, textTransform: "uppercase", marginBottom: spacing.xs }}>
            Capabilities & Skills
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
            {skills.map((skill) => (
              <span
                key={skill}
                style={{
                  fontSize: typography.size.xs,
                  background: colors.border,
                  color: colors.text,
                  padding: `2px ${spacing.xs}px`,
                  borderRadius: spacing.xs,
                }}
              >
                {skill}
              </span>
            ))}
          </div>
        </div>

        {cognitiveFunctions.length > 0 ? (
          <div>
            <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, textTransform: "uppercase", marginBottom: spacing.xs }}>
              Cognitive Functions
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
              {cognitiveFunctions.map((fn) => (
                <span
                  key={fn}
                  style={{
                    fontSize: typography.size.xs,
                    background: colors.border,
                    color: colors.info,
                    padding: `2px ${spacing.xs}px`,
                    borderRadius: spacing.xs,
                  }}
                >
                  {fn}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {/* Recent Activity Log */}
        <div>
          <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, textTransform: "uppercase", marginBottom: spacing.xs }}>
            Recent Activity Log ({activities.length})
          </div>
          {activities.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs, maxHeight: 180, overflowY: "auto" }}>
              {activities.map((act) => (
                <div
                  key={act.activity_id}
                  style={{
                    fontSize: typography.size.xs,
                    padding: spacing.xs,
                    background: colors.background,
                    borderRadius: spacing.xs,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span style={{ color: colors.text }}>{act.message || act.activity_type}</span>
                  <span style={{ color: colors.textMuted }}>{act.status} ({act.progress}%)</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
              No recorded activities yet for this employee.
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

