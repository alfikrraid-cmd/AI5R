import React from "react";
import Badge from "../../../design-system/components/Badge";
import ProgressBar from "../../../design-system/components/ProgressBar";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function MissionDetailModal({ isOpen, onClose, mission }) {
  if (!isOpen || !mission) return null;

  const tasks = mission.tasks || [];
  const plan = mission.execution_plan || {};
  const progress = mission.progress ?? 0;
  const isProduction = Boolean(mission.is_production);

  const statusVariant = mission.status === "COMPLETED" ? "success" : "info";

  return (
    <div
      data-testid="mission-detail-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.sm,
          width: "100%",
          maxWidth: "760px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: `${spacing.md}px ${spacing.lg}px`,
            borderBottom: `1px solid ${colors.border}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div style={{ flex: 1, marginRight: spacing.md }}>
            <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs }}>
              <h2
                data-testid="mission-modal-title"
                style={{
                  margin: 0,
                  color: colors.text,
                  fontSize: typography.size.xl,
                  fontWeight: typography.weight.bold,
                }}
              >
                {mission.title}
              </h2>
              <span data-testid="mission-status-badge">
                <Badge variant={statusVariant}>
                  {mission.status}
                </Badge>
              </span>
              {isProduction ? (
                <span data-testid="mission-production-flag">
                  <Badge variant="warning">
                    PRODUCTION GATE
                  </Badge>
                </span>
              ) : null}
            </div>
            <div
              data-testid="mission-modal-id"
              style={{ fontSize: typography.size.xs, color: colors.textMuted }}
            >
              ID: {mission.mission_id} · Sprint: {mission.sprint_id || "N/A"} · Plan: {mission.plan_id || "N/A"}
            </div>
          </div>
          <button
            type="button"
            data-testid="close-mission-modal"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: colors.textMuted,
              fontSize: typography.size.xl,
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: `${spacing.md}px ${spacing.lg}px`, overflowY: "auto", flex: 1 }}>
          {/* Mission Progress */}
          <div
            style={{
              marginBottom: spacing.lg,
              padding: spacing.md,
              background: colors.background,
              borderRadius: spacing.xs,
              border: `1px solid ${colors.border}`,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: spacing.xs,
              }}
            >
              <span
                style={{
                  fontSize: typography.size.xs,
                  fontWeight: typography.weight.bold,
                  textTransform: "uppercase",
                  color: colors.textMuted,
                }}
              >
                Team Progress (Canonical Derived)
              </span>
              <span
                data-testid="mission-progress-percent"
                style={{
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  color: colors.primary || "#6366f1",
                }}
              >
                {progress}%
              </span>
            </div>
            <ProgressBar value={progress} max={100} />
            {mission.description ? (
              <p
                style={{
                  margin: `${spacing.sm}px 0 0`,
                  fontSize: typography.size.sm,
                  color: colors.text,
                  lineHeight: 1.5,
                }}
              >
                {mission.description}
              </p>
            ) : null}
          </div>

          {/* Execution Plan Topology */}
          <div
            data-testid="mission-execution-plan"
            style={{
              marginBottom: spacing.lg,
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: spacing.sm,
            }}
          >
            <div
              style={{
                padding: spacing.sm,
                background: "rgba(59, 130, 246, 0.1)",
                borderRadius: spacing.xs,
                border: "1px solid rgba(59, 130, 246, 0.3)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>RUNNING</div>
              <div style={{ fontSize: typography.size.lg, fontWeight: "bold", color: "#60a5fa" }}>
                {plan.running?.length || 0}
              </div>
            </div>
            <div
              style={{
                padding: spacing.sm,
                background: "rgba(245, 158, 11, 0.1)",
                borderRadius: spacing.xs,
                border: "1px solid rgba(245, 158, 11, 0.3)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>WAITING</div>
              <div style={{ fontSize: typography.size.lg, fontWeight: "bold", color: "#fbbf24" }}>
                {plan.waiting?.length || 0}
              </div>
            </div>
            <div
              style={{
                padding: spacing.sm,
                background: "rgba(107, 114, 128, 0.1)",
                borderRadius: spacing.xs,
                border: "1px solid rgba(107, 114, 128, 0.3)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>BLOCKED</div>
              <div style={{ fontSize: typography.size.lg, fontWeight: "bold", color: "#9ca3af" }}>
                {plan.blocked?.length || 0}
              </div>
            </div>
            <div
              style={{
                padding: spacing.sm,
                background: "rgba(16, 185, 129, 0.1)",
                borderRadius: spacing.xs,
                border: "1px solid rgba(16, 185, 129, 0.3)",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>COMPLETED</div>
              <div style={{ fontSize: typography.size.lg, fontWeight: "bold", color: "#34d399" }}>
                {plan.completed?.length || 0}
              </div>
            </div>
          </div>

          {/* Decomposed Tasks */}
          <div data-testid="mission-tasks-list">
            <h4
              style={{
                margin: `0 0 ${spacing.sm}px`,
                fontSize: typography.size.sm,
                fontWeight: typography.weight.bold,
                textTransform: "uppercase",
                color: colors.textMuted,
              }}
            >
              Specialist Task Decomposition ({tasks.length})
            </h4>

            <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
              {tasks.map((task) => {
                const isTaskProduction = Boolean(task.is_production || task.metadata?.is_production);
                return (
                  <div
                    key={task.work_item_id}
                    data-testid={`mission-task-${task.assigned_position_id}`}
                    style={{
                      padding: spacing.md,
                      background: colors.background,
                      borderRadius: spacing.xs,
                      border: `1px solid ${colors.border}`,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        marginBottom: spacing.xs,
                      }}
                    >
                      <div>
                        <span
                          data-testid="mission-task-title"
                          style={{
                            color: colors.text,
                            fontSize: typography.size.sm,
                            fontWeight: typography.weight.bold,
                          }}
                        >
                          {task.title}
                        </span>
                        <div
                          data-testid="mission-task-position"
                          style={{
                            fontSize: typography.size.xs,
                            color: colors.textMuted,
                            marginTop: 2,
                          }}
                        >
                          Role: {task.assigned_position_id} · Assigned:{" "}
                          <span
                            data-testid="mission-task-assignee"
                            style={{ color: colors.text, fontWeight: "bold" }}
                          >
                            {task.assigned_employee_name || task.assigned_employee_id || "Unassigned"}
                          </span>
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: spacing.xs }}>
                        {isTaskProduction ? (
                          <span data-testid="mission-task-production-notice">
                            <Badge variant="warning">
                              CHIEF GATE
                            </Badge>
                          </span>
                        ) : null}
                        <span data-testid="mission-task-status">
                          <Badge
                            variant={
                              task.status === "COMPLETED" || task.status === "RELEASED"
                                ? "success"
                                : task.status === "CLAIMED"
                                ? "info"
                                : "neutral"
                            }
                          >
                            {task.status}
                          </Badge>
                        </span>
                      </div>
                    </div>

                    {task.dependencies && task.dependencies.length > 0 ? (
                      <div
                        data-testid="mission-task-dependencies"
                        style={{
                          fontSize: typography.size.xs,
                          color: colors.textMuted,
                          marginTop: spacing.xs,
                        }}
                      >
                        Depends on: {task.dependencies.join(", ")}
                      </div>
                    ) : (
                      <div
                        data-testid="mission-task-dependencies"
                        style={{
                          fontSize: typography.size.xs,
                          color: "#10b981",
                          marginTop: spacing.xs,
                        }}
                      >
                        No dependencies (Root task)
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: `${spacing.md}px ${spacing.lg}px`,
            borderTop: `1px solid ${colors.border}`,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            data-testid="close-mission-modal-btn"
            onClick={onClose}
            style={{
              background: colors.primary || "#6366f1",
              color: "#ffffff",
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.sm}px ${spacing.lg}px`,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            Close Mission View
          </button>
        </div>
      </div>
    </div>
  );
}
