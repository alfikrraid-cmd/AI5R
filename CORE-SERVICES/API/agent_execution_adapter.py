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
    MAX_AUTOMATIC_REVISIONS,
    PatchArtifact,
    PathPolicyValidator,
    PathSecurityError,
    ReviewArtifact,
    RevisionAttempt,
    SandboxManager,
    TestResult,
)
from API.mission_lifecycle import (
    DEFAULT_MAX_REVISION_ITERATIONS,
    MAX_REVISION_ITERATIONS,
    MissionStatus,
    ReviewFinding,
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
        ledger: Any = None,
    ) -> None:
        self.workforce_service = workforce_service
        self.ai_client = ai_client
        self.sandbox_manager = sandbox_manager or SandboxManager(repo_dir=REPO_ROOT)
        self.ledger = ledger
        self._executing_tasks: set[str] = set()
        self._revising_tasks: set[str] = set()
        self._artifacts: dict[str, ExecutionArtifact | PatchArtifact | ReviewArtifact] = {}
        self._artifacts_by_task: dict[str, list[ExecutionArtifact | PatchArtifact | ReviewArtifact]] = {}
        self._revisions: dict[str, RevisionAttempt] = {}
        self._revisions_by_task: dict[str, list[RevisionAttempt]] = {}

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | PatchArtifact | ReviewArtifact | None:
        return self._artifacts.get(artifact_id)

    def get_task_artifacts(self, work_item_id: str) -> list[ExecutionArtifact | PatchArtifact | ReviewArtifact]:
        return list(self._artifacts_by_task.get(work_item_id, []))

    def get_revision(self, revision_id: str) -> RevisionAttempt | None:
        return self._revisions.get(revision_id)

    def get_task_revisions(self, work_item_id: str) -> list[RevisionAttempt]:
        return list(self._revisions_by_task.get(work_item_id, []))

    def get_revision_count(self, work_item_id: str) -> int:
        effective_ledger = self.ledger or getattr(self.workforce_service, "ledger", None)
        if effective_ledger is not None:
            return effective_ledger.get_revision_count(work_item_id)
        return len(self._revisions_by_task.get(work_item_id, []))

    def get_latest_patch(self, work_item_id: str) -> PatchArtifact | None:
        arts = [a for a in self.get_task_artifacts(work_item_id) if isinstance(a, PatchArtifact)]
        return arts[-1] if arts else None

    def get_latest_review(self, work_item_id: str) -> ReviewArtifact | None:
        # Check direct artifacts on this work item or reviews referencing this work item
        direct_reviews = [a for a in self.get_task_artifacts(work_item_id) if isinstance(a, ReviewArtifact)]
        if direct_reviews:
            return direct_reviews[-1]
        # Also check all reviews in memory/ledger that reference artifacts of this work item
        item_patches = {a.artifact_id for a in self.get_task_artifacts(work_item_id) if isinstance(a, PatchArtifact)}
        matching: list[ReviewArtifact] = []
        for art in self._artifacts.values():
            if isinstance(art, ReviewArtifact):
                if any(pid in item_patches for pid in art.reviewed_artifact_ids):
                    matching.append(art)
        return matching[-1] if matching else None

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
        execution_id = f"EXEC-{uuid4().hex[:12].upper()}"

        if employee.position_id in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
            execution_mode = "CONTROLLED_CODING_SANDBOX"
        elif employee.position_id == "QA_ENGINEER" and upstream_patch is not None:
            execution_mode = "ARTIFACT_REVIEW"
        else:
            execution_mode = "READ_ONLY_ANALYSIS"

        effective_ledger = self.ledger or getattr(self.workforce_service, "ledger", None)
        if effective_ledger is not None:
            effective_ledger.record_execution_started(
                execution_id=execution_id,
                work_item_id=work_item.work_item_id,
                employee_id=employee.employee_id,
                role=employee.position_id,
                execution_mode=execution_mode,
                started_at=started_at,
                provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
            )

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
                        metadata={"mission_id": mission_id, "applied_changes": changes},
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

            if effective_ledger is not None:
                try:
                    effective_ledger.record_execution_completed(
                        execution_id=execution_id,
                        status="FAILED",
                        completed_at=_now(),
                        error=str(exc),
                    )
                    effective_ledger.record_artifact(
                        artifact_id=failed_art.artifact_id,
                        work_item_id=work_item.work_item_id,
                        employee_id=employee.employee_id,
                        role=employee.position_id,
                        artifact_type="EXECUTION",
                        status="FAILED",
                        summary=failed_art.summary,
                        payload={"error": str(exc)},
                        execution_id=execution_id,
                        created_at=failed_art.completed_at,
                    )
                except Exception:
                    pass

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

        if effective_ledger is not None:
            effective_ledger.record_execution_completed(
                execution_id=execution_id,
                status="SUCCESS",
                completed_at=completed_at,
            )

            if isinstance(artifact, PatchArtifact):
                art_type = "PATCH"
                parent_art_ids = [a.artifact_id for a in upstream_artifacts]
                test_results_dict = [t.to_dict() for t in artifact.test_results]
            elif isinstance(artifact, ReviewArtifact):
                art_type = "REVIEW"
                parent_art_ids = list(artifact.reviewed_artifact_ids)
                test_results_dict = None
            else:
                art_type = "EXECUTION"
                parent_art_ids = [a.artifact_id for a in upstream_artifacts]
                test_results_dict = None

            effective_ledger.record_artifact(
                artifact_id=artifact.artifact_id,
                work_item_id=work_item.work_item_id,
                employee_id=employee.employee_id,
                role=employee.position_id,
                artifact_type=art_type,
                status=artifact.status,
                summary=artifact.summary,
                payload=artifact.to_dict(),
                parent_artifact_ids=parent_art_ids,
                execution_id=execution_id,
                created_at=completed_at,
                test_results=test_results_dict,
            )
            effective_ledger.update_work_item_status(
                work_item_id=work_item.work_item_id,
                status="COMPLETED",
                artifact_id=artifact.artifact_id,
            )

        # Update WorkforceExecutionPlan if part of a mission
        if plan:
            plan.mark_completed(work_item.work_item_id)
            if effective_ledger is not None:
                effective_ledger.update_plan_state(plan.snapshot())

            ready_items = plan.ready_items()
            for r_id in ready_items:
                r_item = self.workforce_service.find_work_item(r_id)
                if r_item and r_item.status == "PUBLISHED" and r_item.assigned_employee_id:
                    next_emp = self.workforce_service.find_employee(r_item.assigned_employee_id)
                    if next_emp:
                        self.workforce_service.work_board.claim(next_emp, r_item.work_item_id)
                        self.workforce_service.employee_runtime.receive_work(next_emp, r_item)
                        plan.mark_running(r_item.work_item_id)
                        if effective_ledger is not None:
                            effective_ledger.update_work_item_status(
                                work_item_id=r_item.work_item_id,
                                status="CLAIMED",
                                assigned_employee_id=next_emp.employee_id,
                            )
                            effective_ledger.update_plan_state(plan.snapshot())

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

    @staticmethod
    def _merge_applied_changes(
        prior_changes: list[dict[str, Any]],
        new_changes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Deterministically merge prior and new change specs by normalized relative path."""
        merged: dict[str, dict[str, Any]] = {}
        for ch in prior_changes:
            p = ch.get("path", "").replace("\\", "/")
            if p:
                merged[p] = dict(ch)
        for ch in new_changes:
            p = ch.get("path", "").replace("\\", "/")
            if p:
                merged[p] = dict(ch)
        return list(merged.values())

    def check_revision_eligibility(self, work_item_id: str) -> tuple[bool, str]:
        """Verify whether a work item meets all strict backend criteria for autonomous revision."""
        work_item = self.workforce_service.find_work_item(work_item_id)
        if work_item is None:
            return False, f"Work item '{work_item_id}' not found"

        # Canonical role enforcement (strictly derived from canonical work item)
        if work_item.assigned_position_id not in ("BACKEND_ENGINEER", "FRONTEND_ENGINEER"):
            return False, (
                f"Role '{work_item.assigned_position_id}' is not authorized for autonomous revision. "
                "Only BACKEND_ENGINEER and FRONTEND_ENGINEER may perform code revisions."
            )

        if work_item.status in ("RELEASED", "CANCELLED"):
            return False, f"Work item '{work_item_id}' is in status '{work_item.status}' and cannot be revised"

        if work_item_id in self.workforce_service.approval_chain_runtime._chief_approvals:
            return False, f"Work item '{work_item_id}' already has Chief approval"

        if work_item_id in self._executing_tasks or work_item_id in self._revising_tasks:
            return False, f"Work item '{work_item_id}' is currently executing or revising"

        rev_count = self.get_revision_count(work_item_id)
        if rev_count >= MAX_AUTOMATIC_REVISIONS:
            return False, f"Revision limit reached ({rev_count}/{MAX_AUTOMATIC_REVISIONS})"

        latest_review = self.get_latest_review(work_item_id)
        if latest_review is None:
            return False, f"No prior SENTRY review found for work item '{work_item_id}'"

        if latest_review.decision != "REQUEST_CHANGES":
            return False, (
                f"Latest review decision is '{latest_review.decision}'. "
                "Autonomous revision requires REQUEST_CHANGES."
            )

        return True, "Eligible"

    def _format_revision_prompt(
        self,
        work_item: WorkItem,
        employee: DigitalEmployee,
        prior_patch: PatchArtifact,
        review: ReviewArtifact,
    ) -> tuple[str, str]:
        """Construct structured revision context without hidden chain-of-thought."""
        role_instruction = ROLE_INSTRUCTIONS.get(
            employee.position_id,
            f"You are {employee.employee_name}, serving as {employee.position_id}."
        )
        system_prompt = (
            f"{role_instruction}\n"
            f"Employee Name: {employee.employee_name}\n"
            f"Position: {employee.position_id}\n"
            f"Skills: {', '.join(employee.capability_ids)}\n\n"
            "You are revising your implementation based on SENTRY QA technical review findings and test results.\n"
            "You MUST return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "summary": "Concise 1-3 sentence summary of fixes made in this revision",\n'
            '  "changes": [\n'
            '    {"path": "relative/path/to/file", "operation": "modify" or "create", "content": "updated full file content"}\n'
            "  ],\n"
            '  "requested_tests": [\n'
            '    {"kind": "PYTEST", "target": "relative/path/to/test"}\n'
            "  ]\n"
            "}\n"
            "Do NOT include conversational preambles, chain-of-thought, or markdown around the JSON."
        )

        test_lines = [
            f"  * {t.command_id} ({t.target}): {'PASSED' if t.passed else 'FAILED'} (exit {t.exit_code}, {t.duration}s)\n"
            f"    STDOUT: {t.stdout_summary[:500]}\n    STDERR: {t.stderr_summary[:500]}"
            for t in prior_patch.test_results
        ]
        test_str = "\n".join(test_lines) if test_lines else "  No automated tests executed."

        diff_context = prior_patch.git_diff
        if len(diff_context.encode("utf-8")) > 32_768:
            diff_context = diff_context[:32_000] + "\n[DIFF TRUNCATED FOR PROMPT BOUND]"

        user_prompt = (
            f"TASK: {work_item.title}\n"
            f"DESCRIPTION: {work_item.description or 'No additional description'}\n\n"
            "=== SENTRY QA TECHNICAL REVIEW EVIDENCE (REQUEST_CHANGES) ===\n"
            f"Review ID: {review.review_id}\n"
            f"Decision: {review.decision}\n"
            f"Findings: {json.dumps(review.findings)}\n"
            f"Risks: {json.dumps(review.risks)}\n"
            f"Recommended Action: {review.recommended_action}\n\n"
            "=== PREVIOUS PATCH DETAILS ===\n"
            f"Previous Patch ID: {prior_patch.artifact_id}\n"
            f"Previous Summary: {prior_patch.summary}\n"
            f"Changed Files: {', '.join(prior_patch.changed_files)}\n"
            f"Test Results:\n{test_str}\n\n"
            f"Previous Git Diff:\n{diff_context}\n"
            "============================================================\n\n"
            "Instructions:\n"
            "1. Address all technical findings, test failures, and risks identified by SENTRY above.\n"
            "2. Modify or add necessary files in allowed subtrees to fix the issues.\n"
            "3. Request allowlisted automated tests to verify your fix.\n"
            "4. Return ONLY the specified JSON response."
        )
        return system_prompt, user_prompt

    def _perform_sentry_review(
        self,
        work_item: WorkItem,
        sentry_employee: DigitalEmployee | None,
        patch_artifact: PatchArtifact,
        ai_client: Any,
        attempt_number: int,
    ) -> ReviewArtifact:
        """Perform SENTRY QA technical review over PatchArtifact and TestResults."""
        emp = sentry_employee or self.workforce_service.find_employee_by_position("QA_ENGINEER")
        emp_id = emp.employee_id if emp else "EMP-SENTRY"
        emp_name = emp.employee_name if emp else "SENTRY"
        emp_caps = ", ".join(emp.capability_ids) if emp else "automated_testing, review"

        role_instruction = ROLE_INSTRUCTIONS.get("QA_ENGINEER", "You are the AI QA Engineer (SENTRY).")
        system_prompt = (
            f"{role_instruction}\n"
            f"Employee Name: {emp_name}\n"
            "Position: QA_ENGINEER\n"
            f"Skills: {emp_caps}\n\n"
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

        test_lines = [
            f"  * {t.command_id} ({t.target}): {'PASSED' if t.passed else 'FAILED'} (exit {t.exit_code}, {t.duration}s)"
            for t in patch_artifact.test_results
        ]
        test_str = "\n".join(test_lines) if test_lines else "  No automated tests executed."

        user_prompt = (
            f"TASK: Review Patch for '{work_item.title}' (Revision {attempt_number})\n"
            f"UPSTREAM PATCH ARTIFACT: {patch_artifact.role} ({patch_artifact.artifact_id})\n"
            f"Summary: {patch_artifact.summary}\n"
            f"Changed Files: {', '.join(patch_artifact.changed_files)}\n"
            f"Diff Stat:\n{patch_artifact.diff_stat}\n"
            f"Test Results:\n{test_str}\n"
            f"Git Diff:\n{patch_artifact.git_diff}\n"
            "Perform your technical evaluation now and return the required JSON."
        )

        client = ai_client or self.ai_client
        if client is None:
            raise ValueError("SENTRY AI client is not available")

        started_at = _now()
        raw_response = client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            capability="chat",
            metadata={"work_item_id": work_item.work_item_id, "role": "QA_ENGINEER", "review_revision": attempt_number},
        )
        parsed = self._parse_llm_response(raw_response)

        raw_decision = str(parsed.get("decision", "REQUEST_CHANGES")).upper()
        findings = list(parsed.get("findings", []))
        risks = list(parsed.get("risks", []))
        recommended_action = str(parsed.get("recommended_action", ""))

        test_results = patch_artifact.test_results
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
        review_id = f"REV-R{attempt_number}-{uuid4().hex[:8].upper()}"
        structured_findings: list[dict[str, Any]] = []
        effective_ledger = self.ledger or getattr(self.workforce_service, "ledger", None)

        if decision == "REQUEST_CHANGES":
            for idx, finding_text in enumerate(findings):
                f_id = f"FND-QA-{uuid4().hex[:8].upper()}"
                is_test_fail = "test" in str(finding_text).lower() or has_failures
                category = "TEST_FAILURE" if is_test_fail else "FUNCTIONAL_BUG"
                severity = "HIGH" if is_test_fail else "MEDIUM"
                finding_obj = ReviewFinding(
                    finding_id=f_id,
                    severity=severity,
                    category=category,
                    description=str(finding_text),
                    evidence="Exit code != 0 in automated test results" if is_test_fail else str(patch_artifact.diff_stat or "QA review failure"),
                    affected_task_id=work_item.work_item_id,
                    responsible_employee_id=work_item.assigned_employee_id or "",
                    responsible_role=work_item.assigned_position_id,
                    required_action=recommended_action or "Fix failing tests and code regressions in sandbox",
                    status="OPEN",
                )
                structured_findings.append(finding_obj.to_dict())
                if effective_ledger is not None:
                    try:
                        effective_ledger.record_finding(
                            finding_id=f_id,
                            review_id=review_id,
                            work_item_id=work_item.work_item_id,
                            mission_id=work_item.metadata.get("mission_id"),
                            severity=severity,
                            category=category,
                            description=str(finding_text),
                            evidence=finding_obj.evidence,
                            responsible_employee_id=work_item.assigned_employee_id or "",
                            responsible_role=work_item.assigned_position_id,
                            required_action=finding_obj.required_action,
                            status="OPEN",
                        )
                    except Exception:
                        pass

        review = ReviewArtifact(
            review_id=review_id,
            work_item_id=work_item.work_item_id,
            employee_id=emp_id,
            role="QA_ENGINEER",
            reviewed_artifact_ids=[patch_artifact.artifact_id],
            decision=decision,
            findings=findings,
            risks=risks,
            test_evidence_reviewed=test_evidence_reviewed,
            recommended_action=recommended_action,
            started_at=started_at,
            completed_at=completed_at,
            status="COMPLETED",
            provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
            metadata={
                "mission_id": work_item.metadata.get("mission_id"),
                "attempt_number": attempt_number,
                "structured_findings": structured_findings,
            },
        )
        self._artifacts[review.review_id] = review
        self._artifacts_by_task.setdefault(work_item.work_item_id, []).append(review)

        if effective_ledger is not None:
            effective_ledger.record_artifact(
                artifact_id=review.review_id,
                work_item_id=work_item.work_item_id,
                employee_id=emp_id,
                role="QA_ENGINEER",
                artifact_type="REVIEW",
                status="COMPLETED",
                summary=review.summary,
                payload=review.to_dict(),
                parent_artifact_ids=[patch_artifact.artifact_id],
                created_at=completed_at,
            )

        return review

    def _perform_security_review(
        self,
        work_item: WorkItem,
        security_employee: DigitalEmployee | None,
        patch_artifact: PatchArtifact,
        ai_client: Any,
        attempt_number: int = 0,
    ) -> ReviewArtifact:
        """Perform AIGIS Security Review over PatchArtifact and changed files."""
        emp = security_employee or self.workforce_service.find_employee_by_position("SECURITY_ENGINEER")
        emp_id = emp.employee_id if emp else "EMP-AIGIS"
        emp_name = emp.employee_name if emp else "AIGIS"
        emp_caps = ", ".join(emp.capability_ids) if emp else "security_review, vulnerability_analysis"

        role_instruction = ROLE_INSTRUCTIONS.get("SECURITY_ENGINEER", "You are the AI Security Engineer.")
        system_prompt = (
            f"{role_instruction}\n"
            f"Employee Name: {emp_name}\n"
            "Position: SECURITY_ENGINEER\n"
            f"Skills: {emp_caps}\n\n"
            "You are reviewing code patches, changes, and architecture proposals for security vulnerabilities.\n"
            "You MUST return ONLY a JSON object with this exact schema:\n"
            "{\n"
            '  "decision": "APPROVE_TECHNICAL" or "REQUEST_CHANGES",\n'
            '  "summary": "Concise security evaluation summary",\n'
            '  "findings": ["Security finding 1", "Security finding 2"],\n'
            '  "risks": ["Security risk 1", "Security risk 2"],\n'
            '  "recommended_action": "Recommended remediation steps for developers"\n'
            "}\n"
            "CRITICAL SECURITY RULE: If you detect any credential leaks, hardcoded secrets, SQL injection, "
            "path traversal, unauthorized privilege escalation, or auth bypass, you MUST choose 'REQUEST_CHANGES' "
            "and detail the security vulnerability in findings.\n"
            "Do NOT include conversational preambles, chain-of-thought, or markdown around the JSON."
        )

        user_prompt = (
            f"TASK: Security Audit for '{work_item.title}' (Attempt {attempt_number})\n"
            f"PATCH ARTIFACT: {patch_artifact.role} ({patch_artifact.artifact_id})\n"
            f"Summary: {patch_artifact.summary}\n"
            f"Changed Files: {', '.join(patch_artifact.changed_files)}\n"
            f"Diff Stat:\n{patch_artifact.diff_stat}\n"
            f"Git Diff:\n{patch_artifact.git_diff}\n"
            "Perform your security evaluation now and return the required JSON."
        )

        client = ai_client or self.ai_client
        if client is None:
            raise ValueError("Security AI client is not available")

        started_at = _now()
        raw_response = client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            capability="chat",
            metadata={"work_item_id": work_item.work_item_id, "role": "SECURITY_ENGINEER", "review_attempt": attempt_number},
        )
        parsed = self._parse_llm_response(raw_response)

        decision = str(parsed.get("decision", "REQUEST_CHANGES")).upper()
        findings = list(parsed.get("findings", []))
        risks = list(parsed.get("risks", []))
        recommended_action = str(parsed.get("recommended_action", ""))

        # Deterministic security rules / heuristics
        git_diff_lower = (patch_artifact.git_diff or "").lower()
        critical_sec_terms = ["eval(", "exec(", "password=", "secret=", "api_key=", "bearer ", "token="]
        detected_hardcoded_secrets = [term for term in critical_sec_terms if term in git_diff_lower]
        if detected_hardcoded_secrets and decision == "APPROVE_TECHNICAL":
            decision = "REQUEST_CHANGES"
            findings.insert(
                0,
                f"Security policy violation: detected potential hardcoded sensitive token/pattern: {', '.join(detected_hardcoded_secrets)}",
            )

        review_id = f"REV-SEC-R{attempt_number}-{uuid4().hex[:8].upper()}"
        structured_findings: list[dict[str, Any]] = []
        effective_ledger = self.ledger or getattr(self.workforce_service, "ledger", None)

        if decision == "REQUEST_CHANGES":
            for idx, finding_text in enumerate(findings):
                f_id = f"FND-SEC-{uuid4().hex[:8].upper()}"
                finding_obj = ReviewFinding(
                    finding_id=f_id,
                    severity="HIGH",
                    category="SECURITY",
                    description=str(finding_text),
                    evidence=patch_artifact.diff_stat or "Security audit finding",
                    affected_task_id=work_item.work_item_id,
                    responsible_employee_id=work_item.assigned_employee_id or "",
                    responsible_role=work_item.assigned_position_id,
                    required_action=recommended_action or "Remediate security vulnerability in isolated sandbox",
                    status="OPEN",
                )
                structured_findings.append(finding_obj.to_dict())
                if effective_ledger is not None:
                    try:
                        effective_ledger.record_finding(
                            finding_id=f_id,
                            review_id=review_id,
                            work_item_id=work_item.work_item_id,
                            mission_id=work_item.metadata.get("mission_id"),
                            severity="HIGH",
                            category="SECURITY",
                            description=str(finding_text),
                            evidence=finding_obj.evidence,
                            responsible_employee_id=work_item.assigned_employee_id or "",
                            responsible_role=work_item.assigned_position_id,
                            required_action=finding_obj.required_action,
                            status="OPEN",
                        )
                    except Exception:
                        pass

        completed_at = _now()
        review = ReviewArtifact(
            review_id=review_id,
            work_item_id=work_item.work_item_id,
            employee_id=emp_id,
            role="SECURITY_ENGINEER",
            reviewed_artifact_ids=[patch_artifact.artifact_id],
            decision=decision,
            findings=findings,
            risks=risks,
            test_evidence_reviewed={"structured_findings": structured_findings},
            recommended_action=recommended_action,
            started_at=started_at,
            completed_at=completed_at,
            status="COMPLETED",
            provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
            metadata={
                "mission_id": work_item.metadata.get("mission_id"),
                "attempt_number": attempt_number,
                "structured_findings": structured_findings,
            },
        )
        self._artifacts[review.review_id] = review
        self._artifacts_by_task.setdefault(work_item.work_item_id, []).append(review)

        if effective_ledger is not None:
            effective_ledger.record_artifact(
                artifact_id=review.review_id,
                work_item_id=work_item.work_item_id,
                employee_id=emp_id,
                role="SECURITY_ENGINEER",
                artifact_type="REVIEW",
                status="COMPLETED",
                summary=review.summary,
                payload=review.to_dict(),
                parent_artifact_ids=[patch_artifact.artifact_id],
                created_at=completed_at,
            )

        return review

    def execute_revision(
        self,
        work_item_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
    ) -> dict[str, Any]:
        """Execute one autonomous revision cycle for an eligible coding work item."""
        eligible, reason = self.check_revision_eligibility(work_item_id)
        if not eligible:
            raise ValueError(f"Work item '{work_item_id}' not eligible for revision: {reason}")

        work_item = self.workforce_service.find_work_item(work_item_id)
        assert work_item is not None

        assigned_emp_id = work_item.assigned_employee_id
        employee = self.workforce_service.find_employee(assigned_emp_id) if assigned_emp_id else None
        if employee is None:
            raise KeyError(f"Assigned employee '{assigned_emp_id}' not found")

        prior_patch = self.get_latest_patch(work_item_id)
        if prior_patch is None:
            raise ValueError(f"No prior PatchArtifact found for work item '{work_item_id}'")

        latest_review = self.get_latest_review(work_item_id)
        if latest_review is None:
            raise ValueError(f"No prior ReviewArtifact found for work item '{work_item_id}'")

        attempt_number = self.get_revision_count(work_item_id) + 1
        if attempt_number > MAX_AUTOMATIC_REVISIONS:
            raise RuntimeError(
                f"MAX_AUTOMATIC_REVISIONS ({MAX_AUTOMATIC_REVISIONS}) reached. No further automatic revisions permitted."
            )

        revision_id = f"REV-ATTEMPT-{attempt_number}-{uuid4().hex[:8].upper()}"
        revision_obj = RevisionAttempt(
            revision_id=revision_id,
            work_item_id=work_item_id,
            employee_id=employee.employee_id,
            role=employee.position_id,
            attempt_number=attempt_number,
            parent_patch_artifact_id=prior_patch.artifact_id,
            trigger_review_id=latest_review.review_id,
            status="PREPARING",
            created_at=_now(),
            metadata={"attempt_number": attempt_number},
        )

        self._revising_tasks.add(work_item_id)
        effective_ledger = self.ledger or getattr(self.workforce_service, "ledger", None)

        try:
            if effective_ledger is not None:
                effective_ledger.record_revision_attempt(
                    revision_id=revision_id,
                    work_item_id=work_item_id,
                    employee_id=employee.employee_id,
                    role=employee.position_id,
                    attempt_number=attempt_number,
                    parent_patch_artifact_id=prior_patch.artifact_id,
                    trigger_review_id=latest_review.review_id,
                    status="PREPARING",
                    created_at=revision_obj.created_at,
                    metadata=revision_obj.metadata,
                )
            self._revisions[revision_id] = revision_obj
            self._revisions_by_task.setdefault(work_item_id, []).append(revision_obj)

            self.workforce_service.live_stream_api.publish(
                event_type="revision_requested",
                payload={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "attempt_number": attempt_number,
                    "employee_id": employee.employee_id,
                    "role": employee.position_id,
                },
            )

            started_at = _now()
            revision_obj.started_at = started_at
            revision_obj.status = "EXECUTING"
            if effective_ledger is not None:
                effective_ledger.update_revision_status(
                    revision_id=revision_id,
                    status="EXECUTING",
                    started_at=started_at,
                )

            self.workforce_service.live_stream_api.publish(
                event_type="revision_started",
                payload={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "attempt_number": attempt_number,
                    "employee_id": employee.employee_id,
                    "role": employee.position_id,
                },
            )

            # Transition work item on work_board to CLAIMED for the revision cycle
            if work_item_id in self.workforce_service.work_board._completed:
                completed_item = self.workforce_service.work_board._completed.pop(work_item_id)
                completed_item.status = "CLAIMED"
                self.workforce_service.work_board._claimed[work_item_id] = completed_item
            elif work_item_id in self.workforce_service.work_board._published:
                self.workforce_service.work_board.claim(employee, work_item_id)

            if effective_ledger is not None:
                effective_ledger.update_work_item_status(
                    work_item_id=work_item_id,
                    status="CLAIMED",
                )

            # Create NEW disposable sandbox from base commit
            sandbox = self.sandbox_manager.create_sandbox(
                work_item_id=work_item.work_item_id,
                employee_id=employee.employee_id,
            )
            try:
                # Apply prior accepted state
                prior_applied = prior_patch.metadata.get("applied_changes", [])
                if prior_applied:
                    for ch in prior_applied:
                        PathPolicyValidator.validate_change(sandbox.root_path, ch)
                    sandbox.apply_changes(prior_applied)

                # Call specialist AI with structured feedback
                client = ai_client or self.ai_client
                if client is None:
                    raise ValueError("Engineering AI client is not available")

                sys_prompt, u_prompt = self._format_revision_prompt(work_item, employee, prior_patch, latest_review)
                raw_response = client.generate(
                    prompt=u_prompt,
                    system_prompt=sys_prompt,
                    temperature=0.2,
                    capability="chat",
                    metadata={"work_item_id": work_item.work_item_id, "role": employee.position_id, "revision": attempt_number},
                )
                parsed_output = self._parse_llm_response(raw_response)

                changes = parsed_output.get("changes", [])
                requested_tests = parsed_output.get("requested_tests", [])
                if not isinstance(changes, list):
                    raise ValueError("'changes' must be a list of change objects")
                if not isinstance(requested_tests, list):
                    requested_tests = []

                # Validate and apply revision changes
                for ch in changes:
                    PathPolicyValidator.validate_change(sandbox.root_path, ch)
                sandbox.apply_changes(changes)

                # Generate real git diff & stat
                changed_files, diff_stat, git_diff = sandbox.generate_diff()

                # Run real tests
                if effective_ledger is not None:
                    effective_ledger.update_revision_status(revision_id=revision_id, status="TESTING")
                test_results = sandbox.run_tests(requested_tests)

                self.workforce_service.live_stream_api.publish(
                    event_type="revision_tests_completed",
                    payload={
                        "work_item_id": work_item_id,
                        "revision_id": revision_id,
                        "attempt_number": attempt_number,
                        "tests_count": len(test_results),
                        "passed_count": sum(1 for t in test_results if t.passed),
                    },
                )

                # Merge applied changes for cumulative lineage
                cumulative_changes = self._merge_applied_changes(prior_applied, changes)

                # Create new immutable PatchArtifact
                patch_completed_at = _now()
                new_patch = PatchArtifact(
                    artifact_id=f"PATCH-R{attempt_number}-{uuid4().hex[:8].upper()}",
                    work_item_id=work_item.work_item_id,
                    employee_id=employee.employee_id,
                    role=employee.position_id,
                    sandbox_id=sandbox.sandbox_id,
                    base_commit=sandbox.base_commit,
                    summary=parsed_output.get("summary", f"Revision {attempt_number} modifications completed"),
                    changed_files=changed_files,
                    diff_stat=diff_stat,
                    git_diff=git_diff,
                    tests_requested=requested_tests,
                    tests_executed=[{"kind": t.get("kind", ""), "target": t.get("target", "")} for t in requested_tests],
                    test_results=test_results,
                    started_at=started_at,
                    completed_at=patch_completed_at,
                    status="SUCCESS",
                    provider_metadata={"provider": getattr(client, "_default_provider", "router") or "router"},
                    metadata={
                        "mission_id": work_item.metadata.get("mission_id"),
                        "attempt_number": attempt_number,
                        "parent_patch_artifact_id": prior_patch.artifact_id,
                        "applied_changes": cumulative_changes,
                    },
                )
                self._artifacts[new_patch.artifact_id] = new_patch
                self._artifacts_by_task.setdefault(work_item_id, []).append(new_patch)
                work_item.artifact_id = new_patch.artifact_id

                if effective_ledger is not None:
                    test_results_dict = [t.to_dict() for t in new_patch.test_results]
                    effective_ledger.record_artifact(
                        artifact_id=new_patch.artifact_id,
                        work_item_id=work_item.work_item_id,
                        employee_id=employee.employee_id,
                        role=employee.position_id,
                        artifact_type="PATCH",
                        status=new_patch.status,
                        summary=new_patch.summary,
                        payload=new_patch.to_dict(),
                        parent_artifact_ids=[prior_patch.artifact_id, latest_review.review_id],
                        created_at=patch_completed_at,
                        test_results=test_results_dict,
                    )

                self.workforce_service.live_stream_api.publish(
                    event_type="revision_patch_created",
                    payload={
                        "work_item_id": work_item_id,
                        "revision_id": revision_id,
                        "patch_artifact_id": new_patch.artifact_id,
                        "attempt_number": attempt_number,
                        "changed_files": changed_files,
                    },
                )
            finally:
                sandbox.cleanup()

            # Perform SENTRY Technical Review
            if effective_ledger is not None:
                effective_ledger.update_revision_status(revision_id=revision_id, status="REVIEWING")

            self.workforce_service.live_stream_api.publish(
                event_type="revision_review_started",
                payload={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "attempt_number": attempt_number,
                },
            )

            sentry_emp = self.workforce_service.find_employee_by_position("QA_ENGINEER")
            s_client = sentry_client or ai_client or self.ai_client
            review_art = self._perform_sentry_review(
                work_item=work_item,
                sentry_employee=sentry_emp,
                patch_artifact=new_patch,
                ai_client=s_client,
                attempt_number=attempt_number,
            )

            self.workforce_service.live_stream_api.publish(
                event_type="revision_review_completed",
                payload={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "review_id": review_art.review_id,
                    "decision": review_art.decision,
                    "attempt_number": attempt_number,
                },
            )

            # Evaluate review decision
            completed_at = _now()
            revision_obj.completed_at = completed_at

            if review_art.decision == "APPROVE_TECHNICAL":
                revision_obj.status = "COMPLETED"
                if effective_ledger is not None:
                    effective_ledger.update_revision_status(
                        revision_id=revision_id,
                        status="COMPLETED",
                        completed_at=completed_at,
                    )
                    effective_ledger.update_work_item_status(
                        work_item_id=work_item_id,
                        status="COMPLETED",
                        artifact_id=new_patch.artifact_id,
                    )
                self.workforce_service.work_board.complete(employee, work_item_id)
                self.workforce_service.live_stream_api.publish(
                    event_type="revision_approved_technical",
                    payload={
                        "work_item_id": work_item_id,
                        "revision_id": revision_id,
                        "attempt_number": attempt_number,
                    },
                )
                return {
                    "status": "APPROVED",
                    "revision_id": revision_id,
                    "attempt_number": attempt_number,
                    "patch": new_patch,
                    "review": review_art,
                }
            else:
                # SENTRY requested changes
                if attempt_number >= MAX_AUTOMATIC_REVISIONS:
                    # Exhaustion: stop and escalate to Human Chief
                    revision_obj.status = "ESCALATION_REQUIRED"
                    work_item.metadata["recovery_status"] = "ESCALATION_REQUIRED"
                    work_item.metadata["escalation_reason"] = "REVISION_LIMIT_EXHAUSTED"

                    if effective_ledger is not None:
                        effective_ledger.update_revision_status(
                            revision_id=revision_id,
                            status="ESCALATION_REQUIRED",
                            completed_at=completed_at,
                            metadata_update={"escalation_reason": "REVISION_LIMIT_EXHAUSTED"},
                        )
                        effective_ledger.update_work_item_status(
                            work_item_id=work_item_id,
                            status="CLAIMED",
                            recovery_status="ESCALATION_REQUIRED",
                            metadata_update={
                                "recovery_status": "ESCALATION_REQUIRED",
                                "escalation_reason": "REVISION_LIMIT_EXHAUSTED",
                            },
                        )

                    self.workforce_service.live_stream_api.publish(
                        event_type="revision_exhausted",
                        payload={
                            "work_item_id": work_item_id,
                            "revision_id": revision_id,
                            "attempt_number": attempt_number,
                            "reason": "REVISION_LIMIT_EXHAUSTED",
                        },
                    )
                    return {
                        "status": "ESCALATION_REQUIRED",
                        "revision_id": revision_id,
                        "attempt_number": attempt_number,
                        "patch": new_patch,
                        "review": review_art,
                    }
                else:
                    revision_obj.status = "COMPLETED"
                    if effective_ledger is not None:
                        effective_ledger.update_revision_status(
                            revision_id=revision_id,
                            status="COMPLETED",
                            completed_at=completed_at,
                        )
                    return {
                        "status": "REQUEST_CHANGES",
                        "revision_id": revision_id,
                        "attempt_number": attempt_number,
                        "patch": new_patch,
                        "review": review_art,
                    }

        except Exception as exc:
            revision_obj.status = "FAILED"
            revision_obj.error = str(exc)
            revision_obj.completed_at = _now()
            if effective_ledger is not None:
                try:
                    effective_ledger.update_revision_status(
                        revision_id=revision_id,
                        status="FAILED",
                        completed_at=revision_obj.completed_at,
                        error=str(exc),
                    )
                except Exception:
                    pass

            self.workforce_service.live_stream_api.publish(
                event_type="revision_failed",
                payload={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "attempt_number": attempt_number,
                    "error": str(exc),
                },
            )
            raise
        finally:
            self._revising_tasks.discard(work_item_id)

    def execute_revision_cycle(
        self,
        work_item_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
    ) -> dict[str, Any]:
        """Execute the governed autonomous revision loop up to MAX_AUTOMATIC_REVISIONS."""
        results: list[dict[str, Any]] = []
        while True:
            eligible, reason = self.check_revision_eligibility(work_item_id)
            if not eligible:
                break
            res = self.execute_revision(
                work_item_id=work_item_id,
                ai_client=ai_client,
                sentry_client=sentry_client,
            )
            results.append(res)
            if res["status"] in ("APPROVED", "ESCALATION_REQUIRED"):
                break

        latest_res = results[-1] if results else None
        return {
            "status": latest_res["status"] if latest_res else "NO_REVISION_EXECUTED",
            "revision_count": len(results),
            "results": results,
            "latest_patch": latest_res.get("patch") if latest_res else self.get_latest_patch(work_item_id),
            "latest_review": latest_res.get("review") if latest_res else self.get_latest_review(work_item_id),
        }
