import Badge from "../../../design-system/components/Badge";
import ProgressBar from "../../../design-system/components/ProgressBar";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

const STATUS_COLOR_MAP = {
  AVAILABLE: colors.success,
  WORKING: colors.purple,
  WAITING_APPROVAL: colors.warning,
  OFFLINE: colors.textMuted,
};

const STATUS_BADGE_VARIANT = {
  AVAILABLE: "success",
  WORKING: "purple",
  WAITING_APPROVAL: "warning",
  OFFLINE: "info",
};

export default function EmployeeCard({
  employee,
  onInspect,
  onChat,
  onAssign,
  onDelegateProject,
}) {
  if (!employee) return null;

  const isProjectManager =
    employee.position_id === "PROJECT_MANAGER" ||
    employee.employee_name?.toUpperCase() === "NEXA";
  const status = employee.status || "AVAILABLE";
  const statusColor = STATUS_COLOR_MAP[status] || colors.textMuted;
  const badgeVariant = STATUS_BADGE_VARIANT[status] || "info";
  const currentTask = employee.current_task;
  const progress = employee.task_progress ?? 0;
  const skills = employee.skills || [];

  return (
    <article
      className="card"
      data-testid={`employee-card-${employee.position_id}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: spacing.md,
        padding: spacing.md,
        background: colors.panel,
        borderRadius: spacing.sm,
        border: `1px solid ${colors.border}`,
        boxSizing: "border-box",
        position: "relative",
      }}
    >
      {/* Header: Avatar, Name, Position, Status */}
      <div style={{ display: "flex", alignItems: "center", gap: spacing.md }}>
        <div
          style={{
            position: "relative",
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: colors.border,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: typography.size.lg,
            fontWeight: typography.weight.bold,
            color: colors.text,
            flexShrink: 0,
          }}
        >
          {employee.employee_name?.slice(0, 2).toUpperCase() || "AI"}
          <span
            data-testid="status-dot"
            style={{
              position: "absolute",
              bottom: 0,
              right: 0,
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: statusColor,
              border: `2px solid ${colors.panel}`,
            }}
          />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: spacing.xs, flexWrap: "wrap" }}>
            <h3
              style={{
                margin: 0,
                fontSize: typography.size.md,
                fontWeight: typography.weight.bold,
                color: colors.text,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {employee.employee_name}
            </h3>
            <Badge variant={badgeVariant}>{status.replace("_", " ")}</Badge>
          </div>

          <div
            style={{
              fontSize: typography.size.xs,
              color: colors.textMuted,
              marginTop: spacing.xs / 2,
            }}
          >
            {employee.role || employee.title || employee.position_id}
          </div>
        </div>
      </div>

      {/* Task & Progress Section */}
      <div
        style={{
          background: colors.background,
          padding: spacing.sm,
          borderRadius: spacing.xs,
          fontSize: typography.size.xs,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: spacing.xs,
            color: colors.textMuted,
          }}
        >
          <span style={{ fontWeight: typography.weight.bold, textTransform: "uppercase" }}>
            Current Work
          </span>
          <span>{progress}%</span>
        </div>

        <div
          style={{
            color: currentTask ? colors.text : colors.textMuted,
            marginBottom: spacing.xs,
            fontWeight: currentTask ? typography.weight.bold : typography.weight.normal,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={currentTask?.title || "Idle"}
        >
          {currentTask?.title || "Ready for assignment"}
        </div>

        <ProgressBar value={progress} max={100} />
      </div>

      {/* Skills Matrix (Capabilities) */}
      <div>
        <div
          style={{
            fontSize: typography.size.xs,
            color: colors.textMuted,
            marginBottom: spacing.xs,
            textTransform: "uppercase",
            fontWeight: typography.weight.bold,
          }}
        >
          Skills & Capabilities
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
          {skills.slice(0, 4).map((skill) => (
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
          {skills.length > 4 ? (
            <span style={{ fontSize: typography.size.xs, color: colors.textMuted, alignSelf: "center" }}>
              +{skills.length - 4}
            </span>
          ) : null}
        </div>
      </div>

      {/* Action Footer */}
      <div style={{ marginTop: "auto", paddingTop: spacing.xs, display: "flex", gap: spacing.xs, flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="employee-inspect-button"
          onClick={() => onInspect?.(employee)}
          style={{
            flex: "1 1 auto",
            background: "transparent",
            color: colors.text,
            border: `1px solid ${colors.border}`,
            borderRadius: spacing.xs,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            fontSize: typography.size.xs,
            cursor: "pointer",
          }}
        >
          Inspect Profile
        </button>
        <button
          type="button"
          data-testid="employee-chat-button"
          onClick={() => onChat?.(employee)}
          style={{
            flex: "1 1 auto",
            background: "transparent",
            color: colors.info,
            border: `1px solid ${colors.info}`,
            borderRadius: spacing.xs,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            fontSize: typography.size.xs,
            cursor: "pointer",
          }}
        >
          Chat
        </button>
        <button
          type="button"
          data-testid="employee-assign-button"
          onClick={() => onAssign?.(employee)}
          style={{
            flex: "1 1 auto",
            background: colors.info,
            color: colors.text,
            border: "none",
            borderRadius: spacing.xs,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            fontSize: typography.size.xs,
            fontWeight: typography.weight.bold,
            cursor: "pointer",
          }}
        >
          Assign Task
        </button>
        {isProjectManager ? (
          <button
            type="button"
            data-testid="nexa-delegate-project-button"
            onClick={() => onDelegateProject?.(employee)}
            style={{
              flex: "1 1 100%",
              background: "#4f46e5",
              color: "#ffffff",
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.sm}px`,
              fontSize: typography.size.xs,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: spacing.xs,
            }}
          >
            ⚡ Delegate Project
          </button>
        ) : null}
      </div>
    </article>
  );
}

