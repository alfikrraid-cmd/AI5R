import React, { useState, useEffect } from "react";
import Badge from "../../../design-system/components/Badge";
import ProgressBar from "../../../design-system/components/ProgressBar";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";
import {
  orchestrateWorkforceMission,
  fetchMissionFindings,
  fetchMissionEvents,
  approveWorkforceMission,
  rejectWorkforceMission,
} from "../../../api/workforceClient";

export default function MissionDetailModal({ isOpen, onClose, mission, onMissionUpdated }) {
  if (!isOpen || !mission) return null;

  const [currentMission, setCurrentMission] = useState(mission);
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "flow" | "findings" | "events"
  const [findings, setFindings] = useState(mission.findings || []);
  const [events, setEvents] = useState([]);
  const [isOrchestrating, setIsOrchestrating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  useEffect(() => {
    setCurrentMission(mission);
    setFindings(mission.findings || []);
  }, [mission]);

  // Load findings and ledger events on modal open
  useEffect(() => {
    if (!currentMission?.mission_id) return;
    let isMounted = true;

    async function loadDetails() {
      try {
        const [findingsRes, eventsRes] = await Promise.all([
          fetchMissionFindings ? fetchMissionFindings(currentMission.mission_id).catch(() => ({ findings: [] })) : { findings: [] },
          fetchMissionEvents ? fetchMissionEvents(currentMission.mission_id).catch(() => ({ events: [] })) : { events: [] },
        ]);
        if (isMounted) {
          if (findingsRes?.findings) {
            setFindings(findingsRes.findings);
          }
          if (eventsRes?.events) {
            setEvents(eventsRes.events);
          }
        }
      } catch {
        // Fallback to mission embedded data
      }
    }

    loadDetails();
    return () => {
      isMounted = false;
    };
  }, [currentMission?.mission_id]);

  const tasks = currentMission.tasks || [];
  const plan = currentMission.execution_plan || {};
  const progress = currentMission.progress ?? 0;
  const isProduction = Boolean(currentMission.is_production);
  const status = currentMission.status || "DRAFT";
  const currentIteration = currentMission.current_iteration ?? 0;
  const maxIterations = currentMission.max_iterations ?? 3;
  const approvalStatus = currentMission.approval_status || (status === "READY_FOR_CHIEF_APPROVAL" ? "PENDING" : "NOT_REQUESTED");

  // Derive QA status
  const qaReviewResult = currentMission.latest_review_result;
  const qaStatus = qaReviewResult?.decision === "APPROVE_TECHNICAL"
    ? "PASS"
    : qaReviewResult?.decision === "REQUEST_CHANGES"
    ? "FAIL (CHANGES_REQUESTED)"
    : tasks.some((t) => t.assigned_position_id === "QA_ENGINEER" && t.status === "COMPLETED")
    ? "PASS"
    : "PENDING";

  // Derive Security status
  const secReviewResult = currentMission.latest_security_review_result;
  const secStatus = secReviewResult?.decision === "APPROVE_TECHNICAL"
    ? "PASS"
    : secReviewResult?.decision === "REQUEST_CHANGES"
    ? "FAIL (SECURITY_CONCERN)"
    : tasks.some((t) => t.assigned_position_id === "SECURITY_ENGINEER" && t.status === "COMPLETED")
    ? "PASS"
    : "PENDING";

  // Status badge variant
  let statusVariant = "info";
  if (status === "COMPLETED" || status === "APPROVED") {
    statusVariant = "success";
  } else if (status === "READY_FOR_CHIEF_APPROVAL") {
    statusVariant = "warning";
  } else if (status === "REVISION_LIMIT_REACHED" || status === "FAILED" || status === "BLOCKED") {
    statusVariant = "danger";
  } else if (status === "REVISING" || status === "REVISION_REQUIRED") {
    statusVariant = "warning";
  }

  // Handle autonomous orchestration trigger
  async function handleRunOrchestration() {
    setIsOrchestrating(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await orchestrateWorkforceMission(currentMission.mission_id);
      if (res?.mission) {
        setCurrentMission(res.mission);
        if (res.mission.findings) setFindings(res.mission.findings);
        setActionSuccess(`Orchestration completed with status: ${res.mission.status}`);
        if (onMissionUpdated) onMissionUpdated(res.mission);
      }
      // Reload events
      if (fetchMissionEvents) {
        const eventsRes = await fetchMissionEvents(currentMission.mission_id).catch(() => null);
        if (eventsRes?.events) setEvents(eventsRes.events);
      }
    } catch (err) {
      setActionError(err.message || "Orchestration failed");
    } finally {
      setIsOrchestrating(false);
    }
  }

  // Handle Chief Approval
  async function handleChiefApprove() {
    setIsApproving(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await approveWorkforceMission(currentMission.mission_id, {
        approverId: "raid",
        approverRole: "CHIEF_ARCHITECT",
        isHuman: true,
      });
      if (res?.mission) {
        setCurrentMission(res.mission);
        setActionSuccess("Mission successfully approved by Chief!");
        if (onMissionUpdated) onMissionUpdated(res.mission);
      }
    } catch (err) {
      setActionError(err.message || "Approval failed");
    } finally {
      setIsApproving(false);
    }
  }

  // Handle Chief Rejection
  async function handleChiefReject() {
    setIsApproving(true);
    setActionError(null);
    try {
      const res = await rejectWorkforceMission(currentMission.mission_id, {
        approverId: "raid",
        approverRole: "CHIEF_ARCHITECT",
        reason: "Chief requested revisions",
      });
      if (res?.mission) {
        setCurrentMission(res.mission);
        setActionSuccess("Mission rejected by Chief.");
        if (onMissionUpdated) onMissionUpdated(res.mission);
      }
    } catch (err) {
      setActionError(err.message || "Rejection failed");
    } finally {
      setIsApproving(false);
    }
  }

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
          background: colors.surface || colors.panel || "#151C33",
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.sm,
          width: "100%",
          maxWidth: "840px",
          maxHeight: "92vh",
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
            <div style={{ display: "flex", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs, flexWrap: "wrap" }}>
              <h2
                data-testid="mission-modal-title"
                style={{
                  margin: 0,
                  color: colors.text,
                  fontSize: typography.size.xl,
                  fontWeight: typography.weight.bold,
                }}
              >
                {currentMission.title}
              </h2>
              <span data-testid="mission-status-badge">
                <Badge variant={statusVariant}>
                  {status}
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
              ID: {currentMission.mission_id} · Sprint: {currentMission.sprint_id || "N/A"} · Plan: {currentMission.plan_id || "N/A"} · Created By: {currentMission.created_by || "CHIEF"}
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

        {/* Level 6 Metrics & Status Bar */}
        <div
          data-testid="mission-level6-status"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: spacing.xs,
            padding: `${spacing.sm}px ${spacing.lg}px`,
            background: "rgba(0, 0, 0, 0.2)",
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          {/* Revision Loop Status */}
          <div style={{ padding: spacing.xs, textAlign: "center" }}>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>REVISION LOOP</div>
            <div
              data-testid="mission-revision-counter"
              style={{
                fontSize: typography.size.sm,
                fontWeight: "bold",
                color: currentIteration > 0 ? (currentIteration >= maxIterations ? "#EF4444" : "#F59E0B") : "#10B981",
              }}
            >
              Iteration {currentIteration} / {maxIterations}
            </div>
          </div>

          {/* QA Review Status */}
          <div style={{ padding: spacing.xs, textAlign: "center" }}>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>QA REVIEW</div>
            <div
              data-testid="mission-qa-status"
              style={{
                fontSize: typography.size.sm,
                fontWeight: "bold",
                color: qaStatus.startsWith("PASS") ? "#10B981" : qaStatus.startsWith("FAIL") ? "#EF4444" : "#94A3B8",
              }}
            >
              {qaStatus}
            </div>
          </div>

          {/* Security Review Status */}
          <div style={{ padding: spacing.xs, textAlign: "center" }}>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>SECURITY REVIEW</div>
            <div
              data-testid="mission-security-status"
              style={{
                fontSize: typography.size.sm,
                fontWeight: "bold",
                color: secStatus.startsWith("PASS") ? "#10B981" : secStatus.startsWith("FAIL") ? "#EF4444" : "#94A3B8",
              }}
            >
              {secStatus}
            </div>
          </div>

          {/* Chief Approval Gate */}
          <div style={{ padding: spacing.xs, textAlign: "center" }}>
            <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>CHIEF GATE</div>
            <div
              data-testid="mission-chief-approval-status"
              style={{
                fontSize: typography.size.sm,
                fontWeight: "bold",
                color: approvalStatus === "APPROVED" ? "#10B981" : approvalStatus === "PENDING" ? "#F59E0B" : "#94A3B8",
              }}
            >
              {approvalStatus}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            borderBottom: `1px solid ${colors.border}`,
            padding: `0 ${spacing.lg}px`,
            background: colors.background,
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab("overview")}
            style={{
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "overview" ? `2px solid ${colors.info || "#3B82F6"}` : "2px solid transparent",
              color: activeTab === "overview" ? colors.text : colors.textMuted,
              padding: `${spacing.sm}px ${spacing.md}px`,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            Overview & Tasks
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("flow")}
            style={{
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "flow" ? `2px solid ${colors.info || "#3B82F6"}` : "2px solid transparent",
              color: activeTab === "flow" ? colors.text : colors.textMuted,
              padding: `${spacing.sm}px ${spacing.md}px`,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            Autonomous Pipeline Flow
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("findings")}
            style={{
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "findings" ? `2px solid ${colors.info || "#3B82F6"}` : "2px solid transparent",
              color: activeTab === "findings" ? colors.text : colors.textMuted,
              padding: `${spacing.sm}px ${spacing.md}px`,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            Review Findings ({findings.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("events")}
            style={{
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "events" ? `2px solid ${colors.info || "#3B82F6"}` : "2px solid transparent",
              color: activeTab === "events" ? colors.text : colors.textMuted,
              padding: `${spacing.sm}px ${spacing.md}px`,
              fontSize: typography.size.sm,
              fontWeight: typography.weight.bold,
              cursor: "pointer",
            }}
          >
            Execution Ledger ({events.length})
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: `${spacing.md}px ${spacing.lg}px`, overflowY: "auto", flex: 1 }}>
          {/* Action alerts */}
          {actionError ? (
            <div
              data-testid="mission-action-error"
              style={{
                marginBottom: spacing.md,
                padding: spacing.sm,
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                borderRadius: spacing.xs,
                color: "#EF4444",
                fontSize: typography.size.sm,
              }}
            >
              ⚠️ {actionError}
            </div>
          ) : null}
          {actionSuccess ? (
            <div
              data-testid="mission-action-success"
              style={{
                marginBottom: spacing.md,
                padding: spacing.sm,
                background: "rgba(34, 197, 94, 0.15)",
                border: "1px solid rgba(34, 197, 94, 0.4)",
                borderRadius: spacing.xs,
                color: "#22C55E",
                fontSize: typography.size.sm,
              }}
            >
              ✓ {actionSuccess}
            </div>
          ) : null}

          {/* TAB 1: OVERVIEW & TASKS */}
          {activeTab === "overview" && (
            <div>
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
                {currentMission.description ? (
                  <p
                    style={{
                      margin: `${spacing.sm}px 0 0`,
                      fontSize: typography.size.sm,
                      color: colors.text,
                      lineHeight: 1.5,
                    }}
                  >
                    {currentMission.description}
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
          )}

          {/* TAB 2: AUTONOMOUS PIPELINE FLOW */}
          {activeTab === "flow" && (
            <div data-testid="mission-pipeline-flow">
              <h4
                style={{
                  margin: `0 0 ${spacing.md}px`,
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  textTransform: "uppercase",
                  color: colors.textMuted,
                }}
              >
                Level 6 Autonomous Execution & Revision Flow
              </h4>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: spacing.sm,
                  maxWidth: "520px",
                  margin: "0 auto",
                  padding: spacing.md,
                  background: colors.background,
                  borderRadius: spacing.sm,
                  border: `1px solid ${colors.border}`,
                }}
              >
                {/* 1. Chief Mission */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: spacing.sm, background: "rgba(255,255,255,0.03)", borderRadius: spacing.xs }}>
                  <span style={{ fontWeight: "bold", fontSize: typography.size.sm }}>1. Chief Mission Input</span>
                  <span style={{ color: "#10B981" }}>✓ Initialized</span>
                </div>
                <div style={{ textAlign: "center", color: colors.textMuted }}>↓</div>

                {/* 2. NEXA Planning */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: spacing.sm, background: "rgba(255,255,255,0.03)", borderRadius: spacing.xs }}>
                  <span style={{ fontWeight: "bold", fontSize: typography.size.sm }}>2. NEXA Task Decomposition & DAG</span>
                  <span style={{ color: "#10B981" }}>✓ Decomposed ({tasks.length} tasks)</span>
                </div>
                <div style={{ textAlign: "center", color: colors.textMuted }}>↓</div>

                {/* 3. Specialist Execution */}
                <div style={{ padding: spacing.sm, background: "rgba(255,255,255,0.03)", borderRadius: spacing.xs }}>
                  <div style={{ fontWeight: "bold", fontSize: typography.size.sm, marginBottom: spacing.xs }}>3. Specialist Sandbox Execution</div>
                  <div style={{ fontSize: typography.size.xs, color: colors.textMuted, display: "flex", flexDirection: "column", gap: 4 }}>
                    {tasks
                      .filter((t) => !["QA_ENGINEER", "SECURITY_ENGINEER"].includes(t.assigned_position_id))
                      .map((t) => (
                        <div key={t.work_item_id} style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>• {t.assigned_position_id}: {t.title}</span>
                          <span style={{ color: t.status === "COMPLETED" ? "#10B981" : "#F59E0B" }}>
                            {t.status === "COMPLETED" ? "✓" : t.status === "CLAIMED" ? "↻ Running" : "—"}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
                <div style={{ textAlign: "center", color: colors.textMuted }}>↓</div>

                {/* 4. QA Review */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: spacing.sm, background: "rgba(255,255,255,0.03)", borderRadius: spacing.xs }}>
                  <div>
                    <span style={{ fontWeight: "bold", fontSize: typography.size.sm }}>4. QA Verification</span>
                    {findings.length > 0 ? (
                      <div style={{ fontSize: typography.size.xs, color: "#EF4444" }}>
                        ↻ Revision Loop active ({currentIteration} / {maxIterations})
                      </div>
                    ) : null}
                  </div>
                  <span style={{ color: qaStatus.startsWith("PASS") ? "#10B981" : qaStatus.startsWith("FAIL") ? "#EF4444" : "#94A3B8" }}>
                    {qaStatus.startsWith("PASS") ? "✓ Passed" : qaStatus.startsWith("FAIL") ? "✕ Failed → Finding" : "— Waiting"}
                  </span>
                </div>
                <div style={{ textAlign: "center", color: colors.textMuted }}>↓</div>

                {/* 5. Security Review */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: spacing.sm, background: "rgba(255,255,255,0.03)", borderRadius: spacing.xs }}>
                  <span style={{ fontWeight: "bold", fontSize: typography.size.sm }}>5. Security Review</span>
                  <span style={{ color: secStatus.startsWith("PASS") ? "#10B981" : secStatus.startsWith("FAIL") ? "#EF4444" : "#94A3B8" }}>
                    {secStatus.startsWith("PASS") ? "✓ Passed" : secStatus.startsWith("FAIL") ? "✕ Failed" : "— Waiting"}
                  </span>
                </div>
                <div style={{ textAlign: "center", color: colors.textMuted }}>↓</div>

                {/* 6. Chief Approval Gate */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: spacing.sm,
                    background: status === "READY_FOR_CHIEF_APPROVAL" ? "rgba(245, 158, 11, 0.15)" : "rgba(255,255,255,0.03)",
                    border: status === "READY_FOR_CHIEF_APPROVAL" ? "1px solid rgba(245, 158, 11, 0.5)" : "none",
                    borderRadius: spacing.xs,
                  }}
                >
                  <div>
                    <span style={{ fontWeight: "bold", fontSize: typography.size.sm }}>6. Human Chief Approval Gate</span>
                    <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>Controlled release authorization</div>
                  </div>
                  <span style={{ color: approvalStatus === "APPROVED" ? "#10B981" : status === "READY_FOR_CHIEF_APPROVAL" ? "#F59E0B" : "#94A3B8" }}>
                    {approvalStatus === "APPROVED" ? "✓ Approved" : status === "READY_FOR_CHIEF_APPROVAL" ? "⌛ Ready for Chief" : "— Waiting"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: REVIEW FINDINGS */}
          {activeTab === "findings" && (
            <div data-testid="mission-findings-list">
              <h4
                style={{
                  margin: `0 0 ${spacing.sm}px`,
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  textTransform: "uppercase",
                  color: colors.textMuted,
                }}
              >
                Structured Review Findings ({findings.length})
              </h4>

              {findings.length === 0 ? (
                <div style={{ padding: spacing.lg, textAlign: "center", color: colors.textMuted, background: colors.background, borderRadius: spacing.xs, border: `1px solid ${colors.border}` }}>
                  ✓ No open review findings. All completed reviews have satisfied quality standards.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}>
                  {findings.map((f) => (
                    <div
                      key={f.finding_id}
                      data-testid={`finding-item-${f.finding_id}`}
                      style={{
                        padding: spacing.md,
                        background: colors.background,
                        borderRadius: spacing.xs,
                        border: `1px solid ${colors.border}`,
                        borderLeft: `4px solid ${f.severity === "CRITICAL" || f.severity === "HIGH" ? "#EF4444" : "#F59E0B"}`,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: spacing.xs }}>
                        <div>
                          <span style={{ fontWeight: "bold", fontSize: typography.size.sm, color: colors.text }}>
                            {f.finding_id}: {f.description}
                          </span>
                          <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: 2 }}>
                            Category: <strong>{f.category}</strong> · Role: <strong>{f.responsible_role || "ENGINEER"}</strong> · Task: {f.affected_task_id || "N/A"}
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: spacing.xs }}>
                          <Badge variant={f.severity === "CRITICAL" || f.severity === "HIGH" ? "danger" : "warning"}>
                            {f.severity}
                          </Badge>
                          <Badge variant={f.status === "RESOLVED" ? "success" : "info"}>
                            {f.status || "OPEN"}
                          </Badge>
                        </div>
                      </div>

                      {f.required_action ? (
                        <div style={{ fontSize: typography.size.xs, color: colors.text, marginTop: spacing.xs, background: "rgba(255,255,255,0.03)", padding: spacing.xs, borderRadius: spacing.xs }}>
                          <strong>Required Action:</strong> {f.required_action}
                        </div>
                      ) : null}

                      {f.evidence ? (
                        <div style={{ fontSize: typography.size.xs, color: colors.textMuted, marginTop: spacing.xs, fontFamily: "monospace" }}>
                          Evidence: {typeof f.evidence === "string" ? f.evidence : JSON.stringify(f.evidence)}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: EXECUTION LEDGER */}
          {activeTab === "events" && (
            <div data-testid="mission-events-list">
              <h4
                style={{
                  margin: `0 0 ${spacing.sm}px`,
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  textTransform: "uppercase",
                  color: colors.textMuted,
                }}
              >
                Immutable Execution Ledger Events ({events.length})
              </h4>

              {events.length === 0 ? (
                <div style={{ padding: spacing.lg, textAlign: "center", color: colors.textMuted, background: colors.background, borderRadius: spacing.xs, border: `1px solid ${colors.border}` }}>
                  No ledger events recorded yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
                  {events.map((evt, idx) => (
                    <div
                      key={evt.event_id || idx}
                      data-testid={`ledger-event-${evt.event_type}`}
                      style={{
                        padding: `${spacing.xs}px ${spacing.sm}px`,
                        background: colors.background,
                        borderRadius: spacing.xs,
                        border: `1px solid ${colors.border}`,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: "bold", fontSize: typography.size.xs, color: colors.info || "#38bdf8" }}>
                          {evt.event_type}
                        </span>
                        <span style={{ fontSize: typography.size.xs, color: colors.textMuted, marginLeft: spacing.sm }}>
                          by {evt.actor_role || evt.actor_id || "SYSTEM"} ({evt.task_id || "Mission-wide"})
                        </span>
                      </div>
                      <div style={{ fontSize: typography.size.xs, color: colors.textMuted }}>
                        {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : ""}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer with Level 6 Autonomous Orchestration and Chief Approval Controls */}
        <div
          style={{
            padding: `${spacing.md}px ${spacing.lg}px`,
            borderTop: `1px solid ${colors.border}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: colors.background,
          }}
        >
          {/* Autonomous Execution Actions */}
          <div style={{ display: "flex", gap: spacing.sm, alignItems: "center" }}>
            {status !== "COMPLETED" && status !== "APPROVED" && status !== "CANCELLED" ? (
              <button
                type="button"
                data-testid="run-autonomous-loop-btn"
                disabled={isOrchestrating}
                onClick={handleRunOrchestration}
                style={{
                  background: isOrchestrating ? "#4B5563" : "#3B82F6",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: spacing.xs,
                  padding: `${spacing.sm}px ${spacing.md}px`,
                  fontSize: typography.size.sm,
                  fontWeight: typography.weight.bold,
                  cursor: isOrchestrating ? "not-allowed" : "pointer",
                }}
              >
                {isOrchestrating ? "Executing Autonomous Loop..." : "▶ Run Autonomous Loop"}
              </button>
            ) : null}

            {/* Human Chief Approval Gate Controls */}
            {status === "READY_FOR_CHIEF_APPROVAL" && (
              <div data-testid="chief-approval-controls" style={{ display: "flex", gap: spacing.xs }}>
                <button
                  type="button"
                  data-testid="chief-approve-btn"
                  disabled={isApproving}
                  onClick={handleChiefApprove}
                  style={{
                    background: "#10B981",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: spacing.xs,
                    padding: `${spacing.sm}px ${spacing.md}px`,
                    fontSize: typography.size.sm,
                    fontWeight: typography.weight.bold,
                    cursor: isApproving ? "not-allowed" : "pointer",
                  }}
                >
                  ✓ Chief Approve
                </button>
                <button
                  type="button"
                  data-testid="chief-reject-btn"
                  disabled={isApproving}
                  onClick={handleChiefReject}
                  style={{
                    background: "#EF4444",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: spacing.xs,
                    padding: `${spacing.sm}px ${spacing.md}px`,
                    fontSize: typography.size.sm,
                    fontWeight: typography.weight.bold,
                    cursor: isApproving ? "not-allowed" : "pointer",
                  }}
                >
                  ✕ Chief Reject
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            data-testid="close-mission-modal-btn"
            onClick={onClose}
            style={{
              background: "transparent",
              color: colors.textMuted,
              border: `1px solid ${colors.border}`,
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
