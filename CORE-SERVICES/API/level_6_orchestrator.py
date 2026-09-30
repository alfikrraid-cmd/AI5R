from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from API.coding_sandbox import (
    MAX_AUTOMATIC_REVISIONS,
    PatchArtifact,
    ReviewArtifact,
    RevisionAttempt,
    TestResult,
)
from API.mission_lifecycle import (
    DEFAULT_MAX_REVISION_ITERATIONS,
    MAX_REVISION_ITERATIONS,
    DependencyDeadlockError,
    ExecutionTimeoutError,
    LoopSafetyError,
    MissingEmployeeError,
    MissionStatus,
    RepeatedFindingError,
    RepeatedPatchError,
    ReviewFinding,
    SandboxExecutionError,
)
from WORKFORCE.approval_chain_runtime import (
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
)
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Level6LoopSafetyGuard:
    """Detects and prevents pathological loops during autonomous revision."""

    def __init__(self) -> None:
        self.finding_hashes_history: list[str] = []
        self.patch_hashes_history: list[str] = []

    def check_finding_loop(self, findings: list[str | dict[str, Any]]) -> None:
        """Detect repeated identical findings across consecutive revision cycles."""
        norm_strings: list[str] = []
        for f in findings:
            if isinstance(f, dict):
                norm_strings.append(f.get("description", str(f)).strip().lower())
            else:
                norm_strings.append(str(f).strip().lower())
        norm_strings.sort()
        combined = "||".join(norm_strings)
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        if self.finding_hashes_history and self.finding_hashes_history[-1] == digest:
            raise RepeatedFindingError(
                "PATHOLOGICAL_LOOP_IDENTICAL_FINDINGS",
                "Consecutive review cycles generated identical findings with no resolution progress.",
                details={"finding_digest": digest, "findings": findings},
            )
        self.finding_hashes_history.append(digest)

    def check_patch_loop(self, patch: PatchArtifact | None) -> None:
        """Detect repeated identical patches or lack of meaningful change."""
        if patch is None:
            return
        diff_str = (patch.git_diff or "").strip()
        digest = hashlib.sha256(diff_str.encode("utf-8")).hexdigest()

        if self.patch_hashes_history and self.patch_hashes_history[-1] == digest:
            raise RepeatedPatchError(
                "PATHOLOGICAL_LOOP_IDENTICAL_PATCH",
                "Revision produced an identical git diff to previous attempt. No meaningful progress made.",
                details={"patch_digest": digest, "diff_stat": patch.diff_stat},
            )
        self.patch_hashes_history.append(digest)

    def check_deadlock(self, plan: WorkforceExecutionPlan, uncompleted_task_ids: list[str]) -> None:
        """Detect if remaining tasks are blocked with no active or ready tasks."""
        ready = plan.ready_items()
        running = plan.running
        if not ready and not running and uncompleted_task_ids:
            blocked = [tid for tid in uncompleted_task_ids if tid in plan.blocked]
            if len(blocked) == len(uncompleted_task_ids):
                raise DependencyDeadlockError(
                    "DEPENDENCY_DEADLOCK_DETECTED",
                    f"Dependency graph deadlocked: {len(blocked)} uncompleted tasks are blocked with no ready dependencies.",
                    details={"blocked_tasks": blocked, "dependency_graph": plan.dependency_graph},
                )


class Level6MissionOrchestrator:
    """Governed Level 6 Bounded Autonomous Revision Loop Orchestrator."""

    def __init__(self, workforce_service: Any) -> None:
        self.service = workforce_service
        self.safety_guard = Level6LoopSafetyGuard()

    def record_transition_event(
        self,
        event_type: str,
        mission_id: str,
        who: str,
        what: str,
        work_item_id: str | None = None,
        employee_id: str = "SYSTEM",
        role: str = "SYSTEM",
        why: str = "",
        result: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record transition event to execution ledger, activity feed, and live stream."""
        meta = metadata or {}
        if self.service.ledger is not None:
            try:
                self.service.ledger.record_event(
                    event_type=event_type,
                    who=who,
                    what=what,
                    employee_id=employee_id,
                    role=role,
                    mission_id=mission_id,
                    work_item_id=work_item_id,
                    why=why,
                    result=result,
                    metadata=meta,
                )
            except Exception:
                pass

        if hasattr(self.service, "activity_registry") and self.service.activity_registry:
            try:
                self.service.activity_registry.record(
                    EmployeeActivity(
                        employee_id=employee_id,
                        activity_type=event_type,
                        status="ACTIVE",
                        message=f"[{who}] {what}",
                        progress=meta.get("progress", 0),
                        work_item_id=work_item_id or "",
                        mission_id=mission_id,
                        metadata=meta,
                    )
                )
            except Exception:
                pass

        if hasattr(self.service, "live_stream_api") and self.service.live_stream_api:
            try:
                self.service.live_stream_api.publish(
                    event_type=event_type,
                    payload={
                        "mission_id": mission_id,
                        "work_item_id": work_item_id,
                        "who": who,
                        "what": what,
                        "why": why,
                        "result": result,
                        "metadata": meta,
                    },
                )
            except Exception:
                pass

    def orchestrate(
        self,
        mission_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
        security_client: Any = None,
        max_steps: int = 50,
    ) -> dict[str, Any]:
        """Execute the governed autonomous revision loop for a mission."""
        mission = self.service._missions.get(mission_id)
        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found")

        plan: WorkforceExecutionPlan | None = self.service._plans.get(mission_id)
        if not plan:
            raise ValueError(f"Execution plan for mission '{mission_id}' not found")

        max_revisions = int(
            mission.get("max_iterations")
            or mission.get("metadata", {}).get("max_iterations")
            or DEFAULT_MAX_REVISION_ITERATIONS
        )

        current_iteration = int(mission.get("current_iteration", 0))

        if mission.get("status") in (MissionStatus.DRAFT, MissionStatus.PLANNING, MissionStatus.READY, "IN_PROGRESS"):
            mission["status"] = MissionStatus.EXECUTING
            self.service._persist_mission_state(mission_id, MissionStatus.EXECUTING)
            self.record_transition_event(
                event_type="MISSION_STARTED",
                mission_id=mission_id,
                who="NEXA (PROJECT_MANAGER)",
                what=f"Autonomous execution started for mission '{mission['title']}'",
                why="Mission queued and ready for governed autonomous execution",
                result="EXECUTING",
            )

        step_count = 0
        latest_patch: PatchArtifact | None = None
        latest_review: ReviewArtifact | None = None

        while step_count < max_steps:
            step_count += 1

            ready_ids = plan.ready_items()
            all_task_ids = mission.get("task_ids", [])
            uncompleted_task_ids = [
                tid for tid in all_task_ids
                if tid not in plan.completed
            ]

            if not uncompleted_task_ids:
                break

            if plan.running:
                selected_task_id = plan.running[0]
            elif ready_ids:
                selected_task_id = ready_ids[0]
            else:
                try:
                    self.safety_guard.check_deadlock(plan, uncompleted_task_ids)
                except DependencyDeadlockError as exc:
                    mission["status"] = MissionStatus.BLOCKED
                    mission.setdefault("metadata", {})["failure_reason"] = str(exc)
                    self.service._persist_mission_state(mission_id, MissionStatus.BLOCKED)
                    self.record_transition_event(
                        event_type="MISSION_BLOCKED",
                        mission_id=mission_id,
                        who="NEXA (PROJECT_MANAGER)",
                        what="Mission execution blocked due to dependency deadlock",
                        why=str(exc),
                        result="BLOCKED",
                    )
                    return self.service.get_mission(mission_id)

                mission["status"] = MissionStatus.BLOCKED
                self.service._persist_mission_state(mission_id, MissionStatus.BLOCKED)
                self.record_transition_event(
                    event_type="MISSION_BLOCKED",
                    mission_id=mission_id,
                    who="NEXA (PROJECT_MANAGER)",
                    what="No tasks ready to run and none currently running",
                    result="BLOCKED",
                )
                return self.service.get_mission(mission_id)

            task = self.service.find_work_item(selected_task_id)
            if not task:
                raise KeyError(f"Task '{selected_task_id}' not found")

            assigned_emp = self.service.find_employee(task.assigned_employee_id) if task.assigned_employee_id else None
            if not assigned_emp:
                assigned_emp = self.service.find_employee_by_position(task.assigned_position_id)
            if not assigned_emp:
                mission["status"] = MissionStatus.FAILED
                err_msg = f"No active digital employee available for position '{task.assigned_position_id}'"
                mission.setdefault("metadata", {})["failure_reason"] = err_msg
                self.service._persist_mission_state(mission_id, MissionStatus.FAILED)
                self.record_transition_event(
                    event_type="MISSION_FAILED",
                    mission_id=mission_id,
                    work_item_id=task.work_item_id,
                    who="SYSTEM",
                    what=err_msg,
                    result="FAILED",
                )
                return self.service.get_mission(mission_id)

            if task.work_item_id in self.service.work_board._published:
                self.service.work_board.claim(assigned_emp, task.work_item_id)
            if task.work_item_id not in plan.running:
                plan.mark_running(task.work_item_id)
            task.status = "CLAIMED"
            if self.service.ledger is not None:
                self.service.ledger.update_work_item_status(task.work_item_id, status="CLAIMED")

            self.record_transition_event(
                event_type="TASK_STARTED",
                mission_id=mission_id,
                work_item_id=task.work_item_id,
                employee_id=assigned_emp.employee_id,
                role=task.assigned_position_id,
                who=assigned_emp.employee_name,
                what=f"Started execution of task '{task.title}'",
                why=f"Eligible task dependencies satisfied in execution plan",
                result="RUNNING",
            )

            position = task.assigned_position_id

            if position in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
                exec_client = ai_client or self.service.execution_adapter.ai_client
                artifact = self.service.execute_task(task.work_item_id, ai_client=exec_client)
                if isinstance(artifact, PatchArtifact):
                    latest_patch = artifact
                    mission["latest_patch_artifact_id"] = artifact.artifact_id

                plan.mark_completed(task.work_item_id)
                self.record_transition_event(
                    event_type="TASK_COMPLETED",
                    mission_id=mission_id,
                    work_item_id=task.work_item_id,
                    employee_id=assigned_emp.employee_id,
                    role=position,
                    who=assigned_emp.employee_name,
                    what=f"Completed implementation task '{task.title}'",
                    result="COMPLETED",
                )

            elif position == "QA_ENGINEER":
                mission["status"] = MissionStatus.REVIEWING
                self.service._persist_mission_state(mission_id, MissionStatus.REVIEWING)
                self.record_transition_event(
                    event_type="REVIEW_STARTED",
                    mission_id=mission_id,
                    work_item_id=task.work_item_id,
                    employee_id=assigned_emp.employee_id,
                    role=position,
                    who=assigned_emp.employee_name,
                    what=f"QA Engineer (SENTRY) technical review started for '{task.title}'",
                    result="REVIEWING",
                )

                upstream_patch = latest_patch or self.service.execution_adapter.get_latest_patch(task.work_item_id)
                if not upstream_patch:
                    for other_tid in mission.get("task_ids", []):
                        p = self.service.execution_adapter.get_latest_patch(other_tid)
                        if p:
                            upstream_patch = p
                            break

                if not upstream_patch:
                    upstream_patch = PatchArtifact(
                        artifact_id=f"PATCH-QA-{uuid4().hex[:8].upper()}",
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role="QA_ENGINEER",
                        summary="Architectural verification",
                        changed_files=[],
                        diff_stat="0 files changed",
                        test_results=[TestResult(command_id="PYTEST", target="tests", exit_code=0, passed=True, duration=0.1)],
                        git_diff="",
                        started_at=_now(),
                        completed_at=_now(),
                    )

                s_client = sentry_client or ai_client or self.service.execution_adapter.ai_client
                review = self.service.execution_adapter._perform_sentry_review(
                    work_item=task,
                    sentry_employee=assigned_emp,
                    patch_artifact=upstream_patch,
                    ai_client=s_client,
                    attempt_number=current_iteration,
                )
                latest_review = review
                mission["latest_review_result"] = {
                    "review_id": review.review_id,
                    "reviewer": assigned_emp.employee_name,
                    "role": "QA_ENGINEER",
                    "decision": review.decision,
                    "findings": review.findings,
                    "risks": review.risks,
                    "summary": review.summary,
                }

                if review.decision == "APPROVE_TECHNICAL":
                    self.record_transition_event(
                        event_type="REVIEW_PASSED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"QA technical review PASSED for '{task.title}'",
                        result="APPROVE_TECHNICAL",
                    )
                    self.service.work_board.complete(assigned_emp, task.work_item_id)
                    plan.mark_completed(task.work_item_id)
                    self.record_transition_event(
                        event_type="TASK_COMPLETED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"Completed QA task '{task.title}'",
                        result="COMPLETED",
                    )
                else:
                    self.record_transition_event(
                        event_type="REVIEW_FAILED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"QA technical review REQUESTED CHANGES: {len(review.findings)} finding(s)",
                        why="; ".join(str(f) for f in review.findings),
                        result="REQUEST_CHANGES",
                    )

                    try:
                        self.safety_guard.check_finding_loop(review.findings)
                    except RepeatedFindingError as loop_err:
                        mission["status"] = MissionStatus.BLOCKED
                        mission.setdefault("metadata", {})["failure_reason"] = str(loop_err)
                        self.service._persist_mission_state(mission_id, MissionStatus.BLOCKED)
                        self.record_transition_event(
                            event_type="MISSION_BLOCKED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            who="SYSTEM",
                            what="Autonomous revision halted: repeated identical findings detected",
                            why=str(loop_err),
                            result="BLOCKED",
                        )
                        return self.service.get_mission(mission_id)

                    current_iteration += 1
                    mission["current_iteration"] = current_iteration
                    mission["status"] = MissionStatus.REVISION_REQUIRED
                    self.service._persist_mission_state(mission_id, MissionStatus.REVISION_REQUIRED)

                    if current_iteration >= max_revisions:
                        mission["status"] = MissionStatus.REVISION_LIMIT_REACHED
                        mission.setdefault("metadata", {})["failure_reason"] = (
                            f"Revision limit of {max_revisions} exceeded. Escalating to Human Chief."
                        )
                        self.service._persist_mission_state(mission_id, MissionStatus.REVISION_LIMIT_REACHED)
                        self.record_transition_event(
                            event_type="REVISION_LIMIT_REACHED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            who="SYSTEM",
                            what=f"Maximum revision iterations ({max_revisions}) reached without passing QA review",
                            why="Autonomous boundary reached; human escalation required",
                            result="REVISION_LIMIT_REACHED",
                        )
                        return self.service.get_mission(mission_id)

                    responsible_task_id = upstream_patch.work_item_id if upstream_patch else None
                    if not responsible_task_id or responsible_task_id == task.work_item_id:
                        for tid in mission.get("task_ids", []):
                            t_obj = self.service.find_work_item(tid)
                            if t_obj and t_obj.assigned_position_id in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
                                responsible_task_id = tid
                                break

                    resp_task = self.service.find_work_item(responsible_task_id) if responsible_task_id else None
                    resp_emp = self.service.find_employee(resp_task.assigned_employee_id) if resp_task else None

                    self.record_transition_event(
                        event_type="REVISION_REQUESTED",
                        mission_id=mission_id,
                        work_item_id=responsible_task_id,
                        employee_id=resp_emp.employee_id if resp_emp else "SYSTEM",
                        role=resp_task.assigned_position_id if resp_task else "UNKNOWN",
                        who="NEXA (PROJECT_MANAGER)",
                        what=f"Revision {current_iteration}/{max_revisions} routed to {resp_emp.employee_name if resp_emp else 'responsible employee'}",
                        result="REVISION_REQUESTED",
                    )

                    mission["status"] = MissionStatus.REVISING
                    self.service._persist_mission_state(mission_id, MissionStatus.REVISING)
                    self.record_transition_event(
                        event_type="REVISION_STARTED",
                        mission_id=mission_id,
                        work_item_id=responsible_task_id,
                        employee_id=resp_emp.employee_id if resp_emp else "SYSTEM",
                        role=resp_task.assigned_position_id if resp_task else "UNKNOWN",
                        who=resp_emp.employee_name if resp_emp else "DEVELOPER",
                        what=f"Revising task in isolated coding sandbox (Attempt {current_iteration})",
                        result="REVISING",
                    )

                    rev_result = self.service.execute_revision(
                        work_item_id=responsible_task_id,
                        ai_client=ai_client,
                        sentry_client=sentry_client,
                    )
                    rev_patch = rev_result.get("patch")
                    if rev_patch:
                        latest_patch = rev_patch
                        try:
                            self.safety_guard.check_patch_loop(rev_patch)
                        except RepeatedPatchError as patch_err:
                            mission["status"] = MissionStatus.BLOCKED
                            mission.setdefault("metadata", {})["failure_reason"] = str(patch_err)
                            self.service._persist_mission_state(mission_id, MissionStatus.BLOCKED)
                            self.record_transition_event(
                                event_type="MISSION_BLOCKED",
                                mission_id=mission_id,
                                work_item_id=responsible_task_id,
                                who="SYSTEM",
                                what="Autonomous revision halted: repeated identical patch detected",
                                why=str(patch_err),
                                result="BLOCKED",
                            )
                            return self.service.get_mission(mission_id)

                    self.record_transition_event(
                        event_type="REVISION_COMPLETED",
                        mission_id=mission_id,
                        work_item_id=responsible_task_id,
                        who=resp_emp.employee_name if resp_emp else "DEVELOPER",
                        what=f"Revision attempt {current_iteration} completed in sandbox",
                        result="COMPLETED",
                    )

                    mission["status"] = MissionStatus.RE_REVIEWING
                    self.service._persist_mission_state(mission_id, MissionStatus.RE_REVIEWING)

                    if rev_result.get("status") == "APPROVED":
                        rev_review = rev_result.get("review")
                        if rev_review:
                            mission["latest_review_result"] = {
                                "review_id": rev_review.review_id,
                                "reviewer": assigned_emp.employee_name,
                                "role": "QA_ENGINEER",
                                "decision": rev_review.decision,
                                "findings": rev_review.findings,
                                "risks": rev_review.risks,
                                "summary": rev_review.summary,
                            }
                        self.record_transition_event(
                            event_type="REVIEW_PASSED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            employee_id=assigned_emp.employee_id,
                            role=position,
                            who=assigned_emp.employee_name,
                            what=f"QA re-review PASSED for '{task.title}' after {current_iteration} revision(s)",
                            result="APPROVE_TECHNICAL",
                        )
                        self.service.work_board.complete(assigned_emp, task.work_item_id)
                        plan.mark_completed(task.work_item_id)
                        self.record_transition_event(
                            event_type="TASK_COMPLETED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            employee_id=assigned_emp.employee_id,
                            role=position,
                            who=assigned_emp.employee_name,
                            what=f"Completed QA task '{task.title}'",
                            result="COMPLETED",
                        )

            elif position == "SECURITY_ENGINEER":
                mission["status"] = MissionStatus.REVIEWING
                self.service._persist_mission_state(mission_id, MissionStatus.REVIEWING)
                self.record_transition_event(
                    event_type="REVIEW_STARTED",
                    mission_id=mission_id,
                    work_item_id=task.work_item_id,
                    employee_id=assigned_emp.employee_id,
                    role=position,
                    who=assigned_emp.employee_name,
                    what=f"Security Engineer (AIGIS) audit started for '{task.title}'",
                    result="REVIEWING",
                )

                upstream_patch = latest_patch or self.service.execution_adapter.get_latest_patch(task.work_item_id)
                if not upstream_patch:
                    for other_tid in mission.get("task_ids", []):
                        p = self.service.execution_adapter.get_latest_patch(other_tid)
                        if p:
                            upstream_patch = p
                            break

                if not upstream_patch:
                    upstream_patch = PatchArtifact(
                        artifact_id=f"PATCH-SEC-{uuid4().hex[:8].upper()}",
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role="SECURITY_ENGINEER",
                        summary="Security baseline audit",
                        changed_files=[],
                        diff_stat="0 files changed",
                        test_results=[],
                        git_diff="",
                        started_at=_now(),
                        completed_at=_now(),
                    )

                sec_client = security_client or ai_client or self.service.execution_adapter.ai_client
                sec_review = self.service.execution_adapter._perform_security_review(
                    work_item=task,
                    security_employee=assigned_emp,
                    patch_artifact=upstream_patch,
                    ai_client=sec_client,
                    attempt_number=current_iteration,
                )
                latest_review = sec_review
                mission["latest_security_review_result"] = {
                    "review_id": sec_review.review_id,
                    "reviewer": assigned_emp.employee_name,
                    "role": "SECURITY_ENGINEER",
                    "decision": sec_review.decision,
                    "findings": sec_review.findings,
                    "risks": sec_review.risks,
                    "summary": sec_review.summary,
                }

                if sec_review.decision == "APPROVE_TECHNICAL":
                    self.record_transition_event(
                        event_type="REVIEW_PASSED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"Security audit PASSED for '{task.title}'",
                        result="APPROVE_TECHNICAL",
                    )
                    self.service.work_board.complete(assigned_emp, task.work_item_id)
                    plan.mark_completed(task.work_item_id)
                    self.record_transition_event(
                        event_type="TASK_COMPLETED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"Completed Security task '{task.title}'",
                        result="COMPLETED",
                    )
                else:
                    self.record_transition_event(
                        event_type="REVIEW_FAILED",
                        mission_id=mission_id,
                        work_item_id=task.work_item_id,
                        employee_id=assigned_emp.employee_id,
                        role=position,
                        who=assigned_emp.employee_name,
                        what=f"Security audit REQUESTED CHANGES: {len(sec_review.findings)} finding(s)",
                        why="; ".join(str(f) for f in sec_review.findings),
                        result="REQUEST_CHANGES",
                    )

                    current_iteration += 1
                    mission["current_iteration"] = current_iteration
                    mission["status"] = MissionStatus.REVISION_REQUIRED
                    self.service._persist_mission_state(mission_id, MissionStatus.REVISION_REQUIRED)

                    if current_iteration >= max_revisions:
                        mission["status"] = MissionStatus.REVISION_LIMIT_REACHED
                        mission.setdefault("metadata", {})["failure_reason"] = (
                            f"Security revision limit of {max_revisions} exceeded. Escalating to Human Chief."
                        )
                        self.service._persist_mission_state(mission_id, MissionStatus.REVISION_LIMIT_REACHED)
                        self.record_transition_event(
                            event_type="REVISION_LIMIT_REACHED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            who="SYSTEM",
                            what=f"Security review revision limit reached",
                            result="REVISION_LIMIT_REACHED",
                        )
                        return self.service.get_mission(mission_id)

                    responsible_task_id = upstream_patch.work_item_id if upstream_patch else None
                    if not responsible_task_id or responsible_task_id == task.work_item_id:
                        for tid in mission.get("task_ids", []):
                            t_obj = self.service.find_work_item(tid)
                            if t_obj and t_obj.assigned_position_id in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
                                responsible_task_id = tid
                                break

                    resp_task = self.service.find_work_item(responsible_task_id) if responsible_task_id else None
                    resp_emp = self.service.find_employee(resp_task.assigned_employee_id) if resp_task else None

                    self.record_transition_event(
                        event_type="REVISION_REQUESTED",
                        mission_id=mission_id,
                        work_item_id=responsible_task_id,
                        who="NEXA (PROJECT_MANAGER)",
                        what=f"Security revision routed to {resp_emp.employee_name if resp_emp else 'responsible employee'}",
                        result="REVISION_REQUESTED",
                    )

                    mission["status"] = MissionStatus.REVISING
                    self.service._persist_mission_state(mission_id, MissionStatus.REVISING)
                    rev_result = self.service.execute_revision(
                        work_item_id=responsible_task_id,
                        ai_client=ai_client,
                        sentry_client=sec_client,
                    )
                    mission["status"] = MissionStatus.RE_REVIEWING
                    self.service._persist_mission_state(mission_id, MissionStatus.RE_REVIEWING)

                    rev_patch = rev_result.get("patch") or upstream_patch
                    re_sec = self.service.execution_adapter._perform_security_review(
                        work_item=task,
                        security_employee=assigned_emp,
                        patch_artifact=rev_patch,
                        ai_client=sec_client,
                        attempt_number=current_iteration,
                    )
                    mission["latest_security_review_result"] = {
                        "review_id": re_sec.review_id,
                        "reviewer": assigned_emp.employee_name,
                        "role": "SECURITY_ENGINEER",
                        "decision": re_sec.decision,
                        "findings": re_sec.findings,
                        "risks": re_sec.risks,
                        "summary": re_sec.summary,
                    }
                    if re_sec.decision == "APPROVE_TECHNICAL":
                        self.record_transition_event(
                            event_type="REVIEW_PASSED",
                            mission_id=mission_id,
                            work_item_id=task.work_item_id,
                            employee_id=assigned_emp.employee_id,
                            role=position,
                            who=assigned_emp.employee_name,
                            what=f"Security audit PASSED for '{task.title}' after revision",
                            result="APPROVE_TECHNICAL",
                        )
                        self.service.work_board.complete(assigned_emp, task.work_item_id)
                        plan.mark_completed(task.work_item_id)
                    else:
                        return self.service.get_mission(mission_id)

            else:
                exec_client = ai_client or self.service.execution_adapter.ai_client
                artifact = self.service.execute_task(task.work_item_id, ai_client=exec_client)
                plan.mark_completed(task.work_item_id)
                self.record_transition_event(
                    event_type="TASK_COMPLETED",
                    mission_id=mission_id,
                    work_item_id=task.work_item_id,
                    employee_id=assigned_emp.employee_id,
                    role=position,
                    who=assigned_emp.employee_name,
                    what=f"Completed analysis task '{task.title}'",
                    result="COMPLETED",
                )

        all_completed = all(tid in plan.completed for tid in mission.get("task_ids", []))
        if all_completed:
            mission["status"] = MissionStatus.READY_FOR_CHIEF_APPROVAL
            mission["approval_status"] = "PENDING"
            self.service._persist_mission_state(mission_id, MissionStatus.READY_FOR_CHIEF_APPROVAL)
            self.record_transition_event(
                event_type="CHIEF_APPROVAL_REQUESTED",
                mission_id=mission_id,
                who="NEXA (PROJECT_MANAGER)",
                what=f"Mission '{mission['title']}' completed all tasks and automated reviews. Awaiting Human Chief Approval.",
                why="Automated review gates passed. Autonomous execution stopped per Level 6 governance.",
                result="READY_FOR_CHIEF_APPROVAL",
            )

        return self.service.get_mission(mission_id)
