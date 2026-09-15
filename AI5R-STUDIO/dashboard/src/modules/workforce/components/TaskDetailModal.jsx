import { useEffect, useState } from "react";
import { executeWorkforceTask, fetchTaskArtifacts } from "../../../api/workforceClient";
import Badge from "../../../design-system/components/Badge";
import Modal from "../../../design-system/components/Modal";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function TaskDetailModal({
  isOpen,
  onClose,
  task,
  onRequestApproval,
  onTaskExecuted,
}) {
  const [currentTask, setCurrentTask] = useState(task);
  const [artifact, setArtifact] = useState(task?.artifact || null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState(null);

  // Sync state when task prop changes
  useEffect(() => {
    if (!task) return;
    setCurrentTask(task);
    setArtifact(task.artifact || null);
    setError(null);
    setIsExecuting(false);

    // If task has artifact_id but no inline artifact, fetch it
    if (task.artifact_id && !task.artifact) {
      fetchTaskArtifacts(task.work_item_id)
        .then((arts) => {
          if (arts && arts.length > 0) {
            setArtifact(arts[arts.length - 1]);
          }
        })
        .catch(() => {});
    }
  }, [task]);

  if (!isOpen || !task || !currentTask) return null;

  const isProduction = Boolean(
    currentTask.is_production ||
    currentTask.metadata?.is_production ||
    currentTask.metadata?.requires_chief_approval
  );

  const isAwaitingChief =
    currentTask.status === "COMPLETED" && isProduction && !currentTask.metadata?.chief_approval;

  const isClaimed = currentTask.status === "CLAIMED";

  const handleRunAnalysis = async () => {
    if (isExecuting || !isClaimed) return;
    setIsExecuting(true);
    setError(null);

    try {
      const res = await executeWorkforceTask(currentTask.work_item_id);
      if (res.work_item) {
        setCurrentTask(res.work_item);
      } else {
        setCurrentTask((prev) => ({
          ...prev,
          status: "COMPLETED",
          artifact_id: res.artifact?.artifact_id,
        }));
      }
      if (res.artifact) {
        setArtifact(res.artifact);
      }
      onTaskExecuted?.(res);
    } catch (err) {
      setError(err.message || "Execution failed");
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Work Item Details"
    >
      <div
        data-testid="task-detail-modal"
        style={{ display: "flex", flexDirection: "column", gap: spacing.md }}
      >
        {/* Header info */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: typography.size.md, color: colors.text }}>
              {currentTask.title}
            </h3>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: 4 }}>
              ID: <code>{currentTask.work_item_id}</code>
            </div>
          </div>
          <div style={{ display: "flex", gap: spacing.xs }}>
            {isProduction ? <Badge variant="danger">PRODUCTION</Badge> : null}
            <Badge
              variant={
                currentTask.status === "RELEASED"
                  ? "success"
                  : currentTask.status === "COMPLETED"
                  ? "warning"
                  : isClaimed
                  ? "primary"
                  : "purple"
              }
            >
              {currentTask.status}
            </Badge>
          </div>
        </div>

        {/* Description */}
        <div style={{ background: colors.background, padding: spacing.sm, borderRadius: spacing.xs }}>
          <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
            DESCRIPTION
          </div>
          <div style={{ fontSize: typography.size.sm, color: colors.text }}>
            {currentTask.description || "No description provided."}
          </div>
        </div>

        {/* Metadata Details */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.sm,
            fontSize: typography.size.xs,
          }}
        >
          <div style={{ background: colors.background, padding: spacing.sm, borderRadius: spacing.xs }}>
            <span style={{ color: colors.textMuted }}>Assigned Position:</span>
            <div style={{ fontWeight: typography.weight.bold, color: colors.text, marginTop: 2 }}>
              {currentTask.assigned_position_id}
            </div>
          </div>

          <div style={{ background: colors.background, padding: spacing.sm, borderRadius: spacing.xs }}>
            <span style={{ color: colors.textMuted }}>Assigned Employee:</span>
            <div style={{ fontWeight: typography.weight.bold, color: colors.text, marginTop: 2 }}>
              <code>{currentTask.assigned_employee_id || "Unclaimed"}</code>
            </div>
          </div>
        </div>

        {/* Run Analysis Action Button for CLAIMED Tasks */}
        {isClaimed ? (
          <div
            data-testid="task-execution-controls"
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: colors.cardBackground || colors.surface,
              border: `1px solid ${colors.border}`,
              padding: spacing.sm,
              borderRadius: spacing.xs,
            }}
          >
            <div>
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.text }}>
                Phase 1F R1 Execution Seam
              </div>
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                Invoke {currentTask.assigned_position_id} for read-only analysis & proposal generation.
              </div>
            </div>
            <button
              type="button"
              data-testid="run-analysis-button"
              onClick={handleRunAnalysis}
              disabled={isExecuting}
              style={{
                background: isExecuting ? colors.textMuted : (colors.info || "#3b82f6"),
                color: colors.text || "#ffffff",
                border: "none",
                borderRadius: spacing.xs,
                padding: `${spacing.xs}px ${spacing.md}px`,
                fontWeight: typography.weight.bold,
                cursor: isExecuting ? "not-allowed" : "pointer",
                fontSize: typography.size.xs,
              }}
            >
              {isExecuting ? "Running Analysis..." : "Run Analysis"}
            </button>
          </div>
        ) : null}

        {/* Execution Error Banner */}
        {error ? (
          <div
            data-testid="execution-error-banner"
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${colors.danger || "#ef4444"}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              color: colors.danger || "#ef4444",
              fontSize: typography.size.xs,
            }}
          >
            <strong>Execution Error:</strong> {error}
          </div>
        ) : null}

        {/* Execution Artifact View */}
        {artifact ? (
          <div
            data-testid="execution-artifact-view"
            style={{
              background: colors.background,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: spacing.md,
              display: "flex",
              flexDirection: "column",
              gap: spacing.sm,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted }}>
                  EXECUTION ARTIFACT
                </span>
                <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                  ID: <code>{artifact.artifact_id}</code> · Role: <strong>{artifact.role}</strong>
                </div>
              </div>
              <Badge variant="success">{artifact.status}</Badge>
            </div>

            {/* Summary */}
            <div style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}>
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                ANALYSIS SUMMARY
              </div>
              <div style={{ fontSize: typography.size.sm, color: colors.text }}>
                {artifact.summary}
              </div>
            </div>

            {/* Deliverables */}
            {artifact.output?.deliverables ? (
              <div style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}>
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  DELIVERABLES / PROPOSALS
                </div>
                <div style={{ fontSize: typography.size.xs, color: colors.text, whiteSpace: "pre-wrap" }}>
                  {typeof artifact.output.deliverables === "string"
                    ? artifact.output.deliverables
                    : JSON.stringify(artifact.output.deliverables, null, 2)}
                </div>
              </div>
            ) : null}

            {/* Findings */}
            {artifact.output?.findings && Array.isArray(artifact.output.findings) ? (
              <div>
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  KEY FINDINGS
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: typography.size.xs, color: colors.text }}>
                  {artifact.output.findings.map((f, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{f}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Risks & Considerations */}
            {artifact.output?.risks_and_considerations && Array.isArray(artifact.output.risks_and_considerations) ? (
              <div>
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  RISKS & CONSIDERATIONS
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: typography.size.xs, color: colors.textMuted }}>
                  {artifact.output.risks_and_considerations.map((r, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{r}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Metadata Footer */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 10,
                color: colors.textMuted,
                borderTop: `1px solid ${colors.border}`,
                paddingTop: spacing.xs,
              }}
            >
              <span>Started: {artifact.started_at ? new Date(artifact.started_at).toLocaleTimeString() : "N/A"} · Completed: {artifact.completed_at ? new Date(artifact.completed_at).toLocaleTimeString() : "N/A"}</span>
              <span>Provider: {artifact.provider_metadata?.provider || "Router"}</span>
            </div>
          </div>
        ) : null}

        {/* Chief Gate Status if applicable */}
        {isAwaitingChief ? (
          <div
            data-testid="task-awaiting-chief-banner"
            style={{
              background: "rgba(245, 158, 11, 0.15)",
              border: `1px solid ${colors.warning}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: spacing.xs,
            }}
          >
            <div>
              <div style={{ fontWeight: typography.weight.bold, color: colors.warning, fontSize: typography.size.xs }}>
                ⚠️ WAITING CHIEF APPROVAL
              </div>
              <div style={{ fontSize: typography.size.xs, color: colors.text }}>
                Task completed execution, but production release requires explicit Chief authorization.
              </div>
            </div>
            <button
              type="button"
              data-testid="open-approval-from-detail-button"
              onClick={() => {
                onClose();
                onRequestApproval?.(currentTask);
              }}
              style={{
                background: colors.warning || "#f59e0b",
                color: "#000000",
                border: "none",
                borderRadius: spacing.xs,
                padding: `${spacing.xs}px ${spacing.md}px`,
                fontWeight: typography.weight.bold,
                cursor: "pointer",
                fontSize: typography.size.xs,
              }}
            >
              Review & Authorize
            </button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
