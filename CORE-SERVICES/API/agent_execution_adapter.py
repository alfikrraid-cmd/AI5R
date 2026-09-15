from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from API.coding_sandbox import (
    CodingSandbox,
    PatchArtifact,
    PathPolicyValidator,
    PathSecurityError,
    ReviewArtifact,
    SandboxManager,
    TestResult,
)
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.work_item import WorkItem

API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ExecutionArtifact:
    """Canonical structured output of an AI Employee's read-only engineering analysis."""

    artifact_id: str
    work_item_id: str
    employee_id: str
    role: str
    status: str  # "SUCCESS" | "FAILED"
    summary: str
    output: dict[str, Any]
    started_at: str
    completed_at: str
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "work_item_id": self.work_item_id,
            "employee_id": self.employee_id,
            "role": self.role,
            "status": self.status,
            "summary": self.summary,
            "output": self.output,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "provider_metadata": self.provider_metadata,
            "error": self.error,
            "metadata": self.metadata,
        }


ROLE_INSTRUCTIONS: dict[str, str] = {
    "SOLUTION_ARCHITECT": (
        "You are ARCHON, the AI Solution Architect. Analyze the assigned mission/task and provide: "
        "1) Architectural breakdown and system boundaries. "
        "2) Component interactions and data contracts. "
        "3) Constraints and non-functional requirements. "
        "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "BACKEND_ENGINEER": (
        "You are FORGE, the AI Backend Engineer. Analyze the requirements and upstream specifications, "
        "and implement backend services, APIs, data models, or unit tests in the isolated coding sandbox.\n"
        "Allowed subtrees for file modification: CORE-SERVICES/, AI5R-STUDIO/, AI5R-SDK/, PRODUCTS/.\n"
        "All paths must be relative without traversal. Absolute paths, .git, and .env are strictly denied."
    ),
    "FRONTEND_ENGINEER": (
        "You are CANVAS, the AI Frontend Engineer. Analyze the requirements and upstream specifications, "
        "and implement UI components, views, or client state in the isolated coding sandbox.\n"
        "Allowed subtrees for file modification: AI5R-STUDIO/, CORE-SERVICES/, AI5R-SDK/, PRODUCTS/.\n"
        "All paths must be relative without traversal. Absolute paths, .git, and .env are strictly denied."
    ),
    "QA_ENGINEER": (
        "You are the AI QA Engineer (SENTRY). Review the supplied upstream artifacts and provide: "
        "1) Comprehensive test strategy and verification matrix. "
        "2) Edge cases, failure scenarios, and boundary conditions. "
        "3) Quality risks and validation criteria. "
        "CRITICAL TRUTHFULNESS RULE: You are performing artifact review only. You MUST NOT claim "
        "tests passed or failed unless real test execution evidence was supplied to you. "
        "If test results show any failure, you MUST request changes."
    ),
    "DEVOPS_ENGINEER": (
        "You are the AI DevOps Engineer. Analyze the system and provide: "
        "1) Deployment strategy and infrastructure requirements. "
        "2) Observability, logging, and health check specifications. "
        "3) Rollback plan and operational risk analysis. "
        "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT deploy, execute shell commands, or modify infra."
    ),
    "SECURITY_ENGINEER": (
        "You are the AI Security Engineer. Analyze the architecture and proposals and provide: "
        "1) Threat modeling and attack surface analysis. "
        "2) Authentication, authorization, and data isolation audit. "
        "3) Security risks and mitigation recommendations. "
        "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "DOCUMENTATION_ENGINEER": (
        "You are the AI Documentation Engineer. Analyze the system artifacts and provide: "
        "1) Technical documentation outline and architecture overview. "
        "2) API documentation structure. "
        "3) Operator and developer guide proposals. "
        "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files."
    ),
    "PROJECT_MANAGER": (
        "You are NEXA, the AI Project Manager. Analyze the engineering mission and provide: "
        "1) Project objectives and scope breakdown. "
        "2) Specialist work distribution and dependency ordering. "
        "3) Milestone schedule and risk analysis. "
        "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
}


class AgentExecutionAdapter:
    """Connects scheduled canonical WorkItem to real AI execution, producing structured
    ExecutionArtifact, PatchArtifact, or ReviewArtifact, marking WorkBoard completion,
    and passing parent artifacts to dependent child tasks.
    """

    def __init__(
        self,
        workforce_service: Any,
        ai_client: Any = None,
        sandbox_manager: SandboxManager | None = None,
    ) -> None:
        self.workforce_service = workforce_service
        self.ai_client = ai_client
        self.sandbox_manager = sandbox_manager or SandboxManager(repo_dir=REPO_ROOT)
        self._executing_tasks: set[str] = set()
        self._artifacts: dict[str, ExecutionArtifact | PatchArtifact | ReviewArtifact] = {}
        self._artifacts_by_task: dict[str, list[ExecutionArtifact | PatchArtifact | ReviewArtifact]] = {}

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | PatchArtifact | ReviewArtifact | None:
        return self._artifacts.get(artifact_id)

    def get_task_artifacts(self, work_item_id: str) -> list[ExecutionArtifact | PatchArtifact | ReviewArtifact]:
        return list(self._artifacts_by_task.get(work_item_id, []))

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
        """Extract and parse structured JSON from LLM output."""
        text = raw.strip()

        # Handle ```json ... ``` or ``` ... ```
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError(f"LLM output must be a JSON object, got {type(data).__name__}")
            if not data.get("summary"):
                raise ValueError("LLM response missing required 'summary' field")
            return data
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid JSON from AI provider: {err}") from err

    def execute_work_item(
        self,
        work_item_id: str,
        ai_client: Any = None,
    ) -> ExecutionArtifact:
        """Execute a claimed WorkItem through EngineeringAIClient in read-only analysis mode."""
        work_item: WorkItem | None = self.workforce_service.find_work_item(work_item_id)
        if work_item is None:
            raise KeyError(f"Work item not found: {work_item_id}")

        # Idempotency & status gates
        if work_item.status in ("COMPLETED", "RELEASED"):
            raise ValueError(f"Work item '{work_item_id}' is already {work_item.status}")

        if work_item.status != "CLAIMED":
            raise ValueError(
                f"Work item '{work_item_id}' is in status '{work_item.status}', must be CLAIMED to execute"
            )

        if work_item_id in self._executing_tasks:
            raise ValueError(f"Work item '{work_item_id}' is currently executing")

        # If work_item already has an artifact marked SUCCESS, block re-execution
        if work_item.artifact_id and work_item.artifact_id in self._artifacts:
            existing_art = self._artifacts[work_item.artifact_id]
            if existing_art.status == "SUCCESS":
                raise ValueError(
                    f"Work item '{work_item_id}' has already been executed successfully"
                )

        # Resolve assigned employee
        assigned_emp_id = work_item.assigned_employee_id
        if not assigned_emp_id:
            raise ValueError(f"Work item '{work_item_id}' has no assigned employee")

        employee: DigitalEmployee | None = self.workforce_service.find_employee(assigned_emp_id)
        if employee is None:
            raise KeyError(f"Assigned employee '{assigned_emp_id}' not found")

        client = ai_client or self.ai_client
        if client is None:
            raise ValueError("Engineering AI client is not available")

        # Gather upstream parent dependency artifacts as bounded context
        upstream_artifacts: list[ExecutionArtifact | PatchArtifact | ReviewArtifact] = []
        mission_id = work_item.metadata.get("mission_id")
        plan = self.workforce_service._plans.get(mission_id) if mission_id else None

        if plan:
            parent_ids = plan.dependency_graph.get(work_item_id, [])
            for pid in parent_ids:
                parent_arts = self.get_task_artifacts(pid)
                successful_parent = [a for a in parent_arts if a.status in ("SUCCESS", "COMPLETED")]
                if successful_parent:
                    upstream_artifacts.append(successful_parent[-1])

        upstream_patch: PatchArtifact | None = next(
            (a for a in upstream_artifacts if isinstance(a, PatchArtifact)),
            None,
        )

        # Mark in-flight execution state
        self._executing_tasks.add(work_item_id)
        started_at = _now()

        # Record start activity & emit SSE event
        self.workforce_service.activity_registry.record(
            EmployeeActivity(
                employee_id=employee.employee_id,
                activity_type="EXECUTION_STARTED",
                status="EXECUTING",
                message=f"{employee.employee_name} ({employee.position_id}) started execution for '{work_item.title}'",
                progress=50,
                work_item_id=work_item.work_item_id,
                metadata={
                    "role": employee.position_id,
                    "task_title": work_item.title,
                    "mission_id": mission_id,
                },
            )
        )
        self.workforce_service.live_stream_api.publish(
            event_type="WORKFORCE_TASK_EXECUTING",
            payload={
                "work_item_id": work_item.work_item_id,
                "employee_id": employee.employee_id,
                "role": employee.position_id,
                "title": work_item.title,
                "status": "EXECUTING",
            },
        )

        # Build prompt
        role_instruction = ROLE_INSTRUCTIONS.get(
            employee.position_id,
            f"You are {employee.employee_name}, serving as {employee.position_id}. "
            "Provide technical engineering analysis and recommendations. "
            "R1/R2 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands.",
        )

        if employee.position_id in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
            system_prompt = (
                f"{role_instruction}\n"
                f"Employee Name: {employee.employee_name}\n"
                f"Position: {employee.position_id}\n"
                f"Skills: {', '.join(employee.capability_ids)}\n\n"
                "You MUST return ONLY a JSON object with this exact schema:\n"
                "{\n"
                '  "summary": "Concise 1-3 sentence summary of implementation",\n'
                '  "changes": [\n'
                '    {"path": "relative/path/to/file", "operation": "create", "content": "code content"}\n'
                "  ],\n"
                '  "requested_tests": [\n'
                '    {"kind": "PYTEST", "target": "relative/path/to/test"}\n'
                "  ]\n"
                "}\n"
                "Or if performing analysis only without code changes, return:\n"
                "{\n"
                '  "summary": "Concise 1-3 sentence engineering summary",\n'
                '  "findings": ["Key finding 1", "Key finding 2"],\n'
                '  "deliverables": "Detailed analysis/proposals/plans",\n'
                '  "risks_and_considerations": ["Risk or constraint 1", "Risk or constraint 2"]\n'
                "}\n"
                "Do NOT include conversational preambles, chain-of-thought, or markdown around the JSON."
            )
        elif employee.position_id == "QA_ENGINEER" and upstream_patch is not None:
            system_prompt = (
                f"{role_instruction}\n"
                f"Employee Name: {employee.employee_name}\n"
                f"Position: {employee.position_id}\n"
                f"Skills: {', '.join(employee.capability_ids)}\n\n"
                "You are reviewing upstream code patch and automated test results.\n"
                "You MUST return ONLY a JSON object with this exact schema:\n"
                "{\n"
                '  "decision": "APPROVE_TECHNICAL" or "REQUEST_CHANGES",\n'
                '  "summary": "Concise technical evaluation summary",\n'
                '  "findings": ["Technical finding 1", "Technical finding 2"],\n'
                '  "risks": ["Identified risk 1", "Identified risk 2"],\n'
                '  "recommended_action": "Recommended next action for Chief or engineers"\n'
                "}\n"
                "CRITICAL TRUTHFULNESS RULE: If any automated test failed (exit code != 0), "
                "you MUST choose 'REQUEST_CHANGES' and list the test failure as a finding.\n"
                "Do NOT include conversational preambles, chain-of-thought, or markdown around the JSON."
            )
        else:
            system_prompt = (
                f"{role_instruction}\n"
                f"Employee Name: {employee.employee_name}\n"
                f"Position: {employee.position_id}\n"
                f"Skills: {', '.join(employee.capability_ids)}\n\n"
                "You MUST return ONLY a JSON object with this exact schema:\n"
                "{\n"
                '  "summary": "Concise 1-3 sentence engineering summary",\n'
                '  "findings": ["Key finding 1", "Key finding 2"],\n'
                '  "deliverables": "Detailed analysis/proposals/plans",\n'
                '  "risks_and_considerations": ["Risk or constraint 1", "Risk or constraint 2"]\n'
                "}\n"
                "Do NOT include conversational preambles, chain-of-thought, or markdown around the JSON."
            )

        upstream_context = ""
        if upstream_artifacts:
            sections = []
            for art in upstream_artifacts:
                if isinstance(art, PatchArtifact):
                    test_lines = [
                        f"  * {t.command_id} ({t.target}): {'PASSED' if t.passed else 'FAILED'} (exit {t.exit_code}, {t.duration}s)"
                        for t in art.test_results
                    ]
                    test_str = "\n".join(test_lines) if test_lines else "  No automated tests executed."
                    sections.append(
                        f"--- UPSTREAM PATCH ARTIFACT: {art.role} ({art.artifact_id}) ---\n"
                        f"Summary: {art.summary}\n"
                        f"Changed Files: {', '.join(art.changed_files)}\n"
                        f"Diff Stat:\n{art.diff_stat}\n"
                        f"Test Results:\n{test_str}\n"
                        f"Git Diff:\n{art.git_diff}\n"
                        "------------------------------------------------"
                    )
                elif isinstance(art, ReviewArtifact):
                    sections.append(
                        f"--- UPSTREAM REVIEW ARTIFACT: {art.role} ({art.review_id}) ---\n"
                        f"Decision: {art.decision}\n"
                        f"Summary: {art.summary}\n"
                        f"Findings: {json.dumps(art.findings)}\n"
                        f"Risks: {json.dumps(art.risks)}\n"
                        f"Recommended Action: {art.recommended_action}\n"
                        "------------------------------------------------"
                    )
                else:
                    sections.append(
                        f"--- UPSTREAM ARTIFACT: {art.role} ({art.artifact_id}) ---\n"
                        f"Summary: {art.summary}\n"
                        f"Findings: {json.dumps(art.output.get('findings', art.output))}\n"
                        f"Deliverables: {json.dumps(art.output.get('deliverables', ''))}\n"
                        "------------------------------------------------"
                    )
            upstream_context = "\n\nUPSTREAM DEPENDENCY ARTIFACTS:\n" + "\n".join(sections)

        user_prompt = (
            f"TASK: {work_item.title}\n"
            f"DESCRIPTION: {work_item.description or 'No additional description'}\n"
            f"IS_PRODUCTION: {bool(work_item.metadata.get('is_production'))}\n"
            f"{upstream_context}\n\n"
            "Perform your role-specific execution now and return the required JSON."
        )

        # Invoke provider
        try:
            raw_response = client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                capability="chat",
                metadata={"work_item_id": work_item.work_item_id, "role": employee.position_id},
            )
            parsed_output = self._parse_llm_response(raw_response)

            # Security Guard: only BACKEND_ENGINEER and FRONTEND_ENGINEER may write code changes
            has_changes = "changes" in parsed_output and parsed_output["changes"]
            if has_changes and employee.position_id not in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
                raise PermissionError(
                    f"Role '{employee.position_id}' is not authorized to modify source code. "
                    "Only BACKEND_ENGINEER and FRONTEND_ENGINEER have write permissions."
                )

            artifact: ExecutionArtifact | PatchArtifact | ReviewArtifact

            if employee.position_id in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER") and "changes" in parsed_output:
                changes = parsed_output.get("changes", [])
                requested_tests = parsed_output.get("requested_tests", [])
                if not isinstance(changes, list):
                    raise ValueError("'changes' must be a list of change objects")
                if not isinstance(requested_tests, list):
                    requested_tests = []

                sandbox = self.sandbox_manager.create_sandbox(
                    work_item_id=work_item.work_item_id,
                    employee_id=employee.employee_id,
                )
                try:
                    # Validate all changes before applying any
                    for ch in changes:
                        PathPolicyValidator.validate_change(sandbox.root_path, ch)

                    # Apply validated changes to sandbox
                    sandbox.apply_changes(changes)

                    # Generate real git diff & stat
                    changed_files, diff_stat, git_diff = sandbox.generate_diff()

                    # Run allowlisted tests in sandbox
                    test_results = sandbox.run_tests(requested_tests)

                    # Build PatchArtifact
                    completed_at = _now()
                    artifact = PatchArtifact(
                        artifact_id=f"PATCH-{uuid4().hex[:12].upper()}",
                        work_item_id=work_item.work_item_id,
                        employee_id=employee.employee_id,
                        role=employee.position_id,
                        sandbox_id=sandbox.sandbox_id,
                        base_commit=sandbox.base_commit,
                        summary=parsed_output.get("summary", "Sandbox modifications completed"),
                        changed_files=changed_files,
                        diff_stat=diff_stat,
                        git_diff=git_diff,
                        tests_requested=requested_tests,
                        tests_executed=[{"kind": t.get("kind", ""), "target": t.get("target", "")} for t in requested_tests],
                        test_results=test_results,
                        started_at=started_at,
                        completed_at=completed_at,
                        status="SUCCESS",
                        provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
                        metadata={"mission_id": mission_id},
                    )
                finally:
                    sandbox.cleanup()

            elif employee.position_id == "QA_ENGINEER" and (upstream_patch is not None or "decision" in parsed_output):
                raw_decision = str(parsed_output.get("decision", "REQUEST_CHANGES")).upper()
                findings = list(parsed_output.get("findings", []))
                risks = list(parsed_output.get("risks", []))
                recommended_action = str(parsed_output.get("recommended_action", ""))

                test_results = upstream_patch.test_results if upstream_patch else []
                failed_tests = [t for t in test_results if not t.passed or t.exit_code != 0]
                has_failures = len(failed_tests) > 0
                all_passed = (len(test_results) > 0) and (not has_failures)

                decision = raw_decision
                if has_failures and decision == "APPROVE_TECHNICAL":
                    decision = "REQUEST_CHANGES"
                    findings.insert(
                        0,
                        f"Automated test verification failed: {len(failed_tests)} test(s) failed with non-zero exit code. Technical approval denied.",
                    )

                test_evidence_reviewed = {
                    "total_tests": len(test_results),
                    "passed_tests": sum(1 for t in test_results if t.passed and t.exit_code == 0),
                    "failed_tests": len(failed_tests),
                    "all_passed": all_passed,
                    "tests": [t.to_dict() for t in test_results],
                }

                completed_at = _now()
                artifact = ReviewArtifact(
                    review_id=f"REV-{uuid4().hex[:12].upper()}",
                    work_item_id=work_item.work_item_id,
                    employee_id=employee.employee_id,
                    role=employee.position_id,
                    reviewed_artifact_ids=[upstream_patch.artifact_id] if upstream_patch else [],
                    decision=decision,
                    findings=findings,
                    risks=risks,
                    test_evidence_reviewed=test_evidence_reviewed,
                    recommended_action=recommended_action,
                    started_at=started_at,
                    completed_at=completed_at,
                    status="COMPLETED",
                    provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
                    metadata={"mission_id": mission_id},
                )

            else:
                completed_at = _now()
                artifact = ExecutionArtifact(
                    artifact_id=f"ART-{uuid4().hex[:12].upper()}",
                    work_item_id=work_item.work_item_id,
                    employee_id=employee.employee_id,
                    role=employee.position_id,
                    status="SUCCESS",
                    summary=parsed_output.get("summary", "Analysis completed successfully"),
                    output=parsed_output,
                    started_at=started_at,
                    completed_at=completed_at,
                    provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
                    metadata={"mission_id": mission_id},
                )

        except Exception as exc:
            self._executing_tasks.discard(work_item_id)
            failed_art = ExecutionArtifact(
                artifact_id=f"ART-ERR-{uuid4().hex[:8].upper()}",
                work_item_id=work_item.work_item_id,
                employee_id=employee.employee_id,
                role=employee.position_id,
                status="FAILED",
                summary=f"Execution failed: {str(exc)}",
                output={},
                started_at=started_at,
                completed_at=_now(),
                error=str(exc),
                provider_metadata={"error_type": type(exc).__name__},
            )
            self._artifacts[failed_art.artifact_id] = failed_art
            self._artifacts_by_task.setdefault(work_item_id, []).append(failed_art)

            # Record failure activity (progress 0)
            self.workforce_service.activity_registry.record(
                EmployeeActivity(
                    employee_id=employee.employee_id,
                    activity_type="EXECUTION_FAILED",
                    status="FAILED",
                    message=f"{employee.employee_name} execution failed: {str(exc)}",
                    progress=0,
                    work_item_id=work_item.work_item_id,
                    metadata={"error": str(exc)},
                )
            )
            self.workforce_service.live_stream_api.publish(
                event_type="WORKFORCE_TASK_FAILED",
                payload={
                    "work_item_id": work_item.work_item_id,
                    "employee_id": employee.employee_id,
                    "error": str(exc),
                },
            )
            # Safe preservation: task remains CLAIMED on WorkBoard!
            raise RuntimeError(f"Agent execution failed for task '{work_item_id}': {exc}") from exc

        # Execution succeeded: save artifact
        self._executing_tasks.discard(work_item_id)
        self._artifacts[artifact.artifact_id] = artifact
        self._artifacts_by_task.setdefault(work_item_id, []).append(artifact)
        work_item.artifact_id = artifact.artifact_id

        # Mark task completed on WorkBoard
        self.workforce_service.work_board.complete(employee, work_item.work_item_id)

        # Update WorkforceExecutionPlan if part of a mission
        if plan:
            plan.mark_completed(work_item.work_item_id)
            ready_items = plan.ready_items()
            for r_id in ready_items:
                r_item = self.workforce_service.find_work_item(r_id)
                if r_item and r_item.status == "PUBLISHED" and r_item.assigned_employee_id:
                    next_emp = self.workforce_service.find_employee(r_item.assigned_employee_id)
                    if next_emp:
                        self.workforce_service.work_board.claim(next_emp, r_item.work_item_id)
                        self.workforce_service.employee_runtime.receive_work(next_emp, r_item)
                        plan.mark_running(r_item.work_item_id)

        # Record activity & emit events depending on artifact type
        if isinstance(artifact, PatchArtifact):
            self.workforce_service.activity_registry.record(
                EmployeeActivity(
                    employee_id=employee.employee_id,
                    activity_type="PATCH_CREATED",
                    status="COMPLETED",
                    message=f"{employee.employee_name} created sandbox patch for '{work_item.title}' ({len(artifact.changed_files)} files)",
                    progress=100,
                    work_item_id=work_item.work_item_id,
                    metadata={"artifact_id": artifact.artifact_id, "changed_files": artifact.changed_files},
                )
            )
            self.workforce_service.live_stream_api.publish(
                event_type="WORKFORCE_PATCH_CREATED",
                payload={
                    "artifact_id": artifact.artifact_id,
                    "work_item_id": work_item.work_item_id,
                    "employee_id": employee.employee_id,
                    "role": employee.position_id,
                    "summary": artifact.summary,
                    "changed_files": artifact.changed_files,
                    "diff_stat": artifact.diff_stat,
                },
            )
        elif isinstance(artifact, ReviewArtifact):
            self.workforce_service.activity_registry.record(
                EmployeeActivity(
                    employee_id=employee.employee_id,
                    activity_type="REVIEW_COMPLETED",
                    status="COMPLETED",
                    message=f"{employee.employee_name} completed technical review for '{work_item.title}': {artifact.decision}",
                    progress=100,
                    work_item_id=work_item.work_item_id,
                    metadata={"artifact_id": artifact.artifact_id, "decision": artifact.decision},
                )
            )
            self.workforce_service.live_stream_api.publish(
                event_type="WORKFORCE_REVIEW_CREATED",
                payload={
                    "artifact_id": artifact.artifact_id,
                    "work_item_id": work_item.work_item_id,
                    "employee_id": employee.employee_id,
                    "role": employee.position_id,
                    "decision": artifact.decision,
                    "summary": artifact.summary,
                },
            )
        else:
            self.workforce_service.activity_registry.record(
                EmployeeActivity(
                    employee_id=employee.employee_id,
                    activity_type="ARTIFACT_CREATED",
                    status="COMPLETED",
                    message=f"{employee.employee_name} completed analysis artifact for '{work_item.title}'",
                    progress=100,
                    work_item_id=work_item.work_item_id,
                    metadata={"artifact_id": artifact.artifact_id},
                )
            )

        # Generic SSE events for cross-module compatibility
        self.workforce_service.live_stream_api.publish(
            event_type="WORKFORCE_ARTIFACT_CREATED",
            payload={
                "artifact_id": artifact.artifact_id,
                "work_item_id": work_item.work_item_id,
                "employee_id": employee.employee_id,
                "role": employee.position_id,
                "summary": artifact.summary,
            },
        )
        self.workforce_service.live_stream_api.publish(
            event_type="WORKFORCE_TASK_COMPLETED",
            payload={
                "work_item_id": work_item.work_item_id,
                "employee_id": employee.employee_id,
                "status": "COMPLETED",
                "artifact_id": artifact.artifact_id,
            },
        )

        return artifact
