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

  const isCodingRole =
    currentTask.assigned_position_id === "BACKEND_ENGINEER" ||
    currentTask.assigned_position_id === "FRONTEND_ENGINEER";

  const isPatch = Boolean(
    artifact && (artifact.sandbox_id || artifact.git_diff !== undefined || artifact.changed_files !== undefined)
  );

  const isReview = Boolean(
    artifact && (artifact.review_id || artifact.decision !== undefined)
  );

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

        {/* Execution Action Controls for CLAIMED Tasks */}
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
                {isCodingRole ? "Controlled Coding Sandbox" : "Phase 1F Execution Seam"}
              </div>
              <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                {isCodingRole
                  ? `Execute ${currentTask.assigned_position_id} in isolated worktree sandbox with real diff & tests.`
                  : `Invoke ${currentTask.assigned_position_id} for engineering analysis & proposal generation.`}
              </div>
            </div>
            <button
              type="button"
              data-testid="run-analysis-button"
              onClick={handleRunAnalysis}
              disabled={isExecuting}
              style={{
                background: isExecuting
                  ? colors.textMuted
                  : isCodingRole
                  ? (colors.success || "#10b981")
                  : (colors.info || "#3b82f6"),
                color: colors.text || "#ffffff",
                border: "none",
                borderRadius: spacing.xs,
                padding: `${spacing.xs}px ${spacing.md}px`,
                fontWeight: typography.weight.bold,
                cursor: isExecuting ? "not-allowed" : "pointer",
                fontSize: typography.size.xs,
              }}
            >
              {isExecuting
                ? (isCodingRole ? "Running in Sandbox..." : "Running Analysis...")
                : (isCodingRole ? "Run in Sandbox" : "Run Analysis")}
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

        {/* Patch Artifact View (Sandbox Execution) */}
        {artifact && isPatch ? (
          <div
            data-testid="patch-artifact-view"
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
                  SANDBOX PATCH ARTIFACT
                </span>
                <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                  ID: <code>{artifact.artifact_id}</code> · Sandbox: <code>{artifact.sandbox_id || "Isolated"}</code>
                  {artifact.base_commit ? ` · Base: ${artifact.base_commit.slice(0, 8)}` : ""}
                </div>
              </div>
              <Badge variant={artifact.status === "SUCCESS" ? "success" : "danger"}>{artifact.status}</Badge>
            </div>

            {/* Patch Summary */}
            <div style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}>
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                PATCH SUMMARY
              </div>
              <div style={{ fontSize: typography.size.sm, color: colors.text }}>
                {artifact.summary}
              </div>
            </div>

            {/* Changed Files */}
            <div
              data-testid="patch-changed-files"
              style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
            >
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                MODIFIED SOURCE FILES ({artifact.changed_files?.length || 0})
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: typography.size.xs, color: colors.text }}>
                {(artifact.changed_files || []).map((file, i) => (
                  <li key={i}>
                    <code>{file}</code>
                  </li>
                ))}
              </ul>
            </div>

            {/* Diff Stat */}
            {artifact.diff_stat ? (
              <div
                data-testid="patch-diff-stat"
                style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
              >
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  DIFF STAT
                </div>
                <pre style={{ margin: 0, fontSize: 11, color: colors.textMuted, whiteSpace: "pre-wrap" }}>
                  {artifact.diff_stat}
                </pre>
              </div>
            ) : null}

            {/* Real Git Diff */}
            <div
              data-testid="patch-git-diff"
              style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
            >
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                GIT DIFF (SANDBOX WORKTREE)
              </div>
              <pre
                style={{
                  margin: 0,
                  fontSize: 11,
                  fontFamily: "monospace",
                  background: "#0d1117",
                  color: "#e6edf3",
                  padding: spacing.sm,
                  borderRadius: spacing.xs,
                  overflowX: "auto",
                  maxHeight: 250,
                  whiteSpace: "pre-wrap",
                }}
              >
                {artifact.git_diff || "(No diff generated)"}
              </pre>
            </div>

            {/* Test Results */}
            <div
              data-testid="patch-test-results"
              style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
            >
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                TEST EXECUTION RESULTS ({artifact.test_results?.length || 0})
              </div>
              {artifact.test_results && artifact.test_results.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
                  {artifact.test_results.map((t, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: spacing.xs,
                        background: colors.background,
                        borderRadius: spacing.xs,
                        fontSize: typography.size.xs,
                      }}
                    >
                      <div>
                        <strong>{t.command_id}</strong> on <code>{t.target}</code>
                        <span style={{ color: colors.textMuted, marginLeft: 8 }}>({t.duration}s)</span>
                      </div>
                      <Badge variant={t.passed ? "success" : "danger"}>
                        {t.passed ? "PASSED" : `FAILED (exit ${t.exit_code})`}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                  No automated tests requested or executed.
                </div>
              )}
            </div>

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
              <span>Isolated Git Worktree Sandbox</span>
            </div>
          </div>
        ) : null}

        {/* Review Artifact View (SENTRY Technical Review) */}
        {artifact && isReview ? (
          <div
            data-testid="review-artifact-view"
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
                  TECHNICAL REVIEW (SENTRY)
                </span>
                <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                  ID: <code>{artifact.review_id || artifact.artifact_id}</code> · Role: <strong>{artifact.role || "QA_ENGINEER"}</strong>
                </div>
              </div>
              <Badge variant={artifact.decision === "APPROVE_TECHNICAL" ? "success" : "warning"}>
                {artifact.decision}
              </Badge>
            </div>

            {/* Review Summary */}
            <div style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}>
              <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                REVIEW EVALUATION
              </div>
              <div style={{ fontSize: typography.size.sm, color: colors.text }}>
                {artifact.summary}
              </div>
            </div>

            {/* Findings */}
            {artifact.findings && artifact.findings.length > 0 ? (
              <div
                data-testid="review-findings"
                style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
              >
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  TECHNICAL FINDINGS ({artifact.findings.length})
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: typography.size.xs, color: colors.text }}>
                  {artifact.findings.map((f, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{f}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Risks */}
            {artifact.risks && artifact.risks.length > 0 ? (
              <div
                data-testid="review-risks"
                style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
              >
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  IDENTIFIED RISKS ({artifact.risks.length})
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: typography.size.xs, color: colors.textMuted }}>
                  {artifact.risks.map((r, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{r}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Test Evidence Reviewed */}
            {artifact.test_evidence_reviewed ? (
              <div
                data-testid="review-test-evidence"
                style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}
              >
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  AUTOMATED TEST EVIDENCE REVIEWED
                </div>
                <div style={{ fontSize: typography.size.xs, color: colors.text }}>
                  Total tests: <strong>{artifact.test_evidence_reviewed.total_tests || 0}</strong> · Passed: <strong style={{ color: "#10b981" }}>{artifact.test_evidence_reviewed.passed_tests || 0}</strong> · Failed: <strong style={{ color: "#ef4444" }}>{artifact.test_evidence_reviewed.failed_tests || 0}</strong>
                </div>
              </div>
            ) : null}

            {/* Recommended Action */}
            {artifact.recommended_action ? (
              <div style={{ background: colors.surface || colors.cardBackground, padding: spacing.sm, borderRadius: spacing.xs }}>
                <div style={{ fontSize: typography.size.xs, fontWeight: typography.weight.bold, color: colors.textMuted, marginBottom: 4 }}>
                  RECOMMENDED ACTION
                </div>
                <div style={{ fontSize: typography.size.xs, color: colors.text }}>
                  {artifact.recommended_action}
                </div>
              </div>
            ) : null}

            {/* Human Gate Advisory */}
            <div
              style={{
                background: "rgba(59, 130, 246, 0.1)",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                padding: spacing.xs,
                borderRadius: spacing.xs,
                fontSize: 11,
                color: colors.info || "#3b82f6",
              }}
            >
              ℹ️ Technical evaluation only. Production release remains strictly guarded by the Human Chief Gate.
            </div>

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
              <span>SENTRY Quality Gate</span>
            </div>
          </div>
        ) : null}

        {/* Standard Execution Artifact View (Analysis) */}
        {artifact && !isPatch && !isReview ? (
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
