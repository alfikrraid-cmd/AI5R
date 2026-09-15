from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.work_item import WorkItem


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
        "You are the AI Solution Architect. Analyze the assigned mission/task and provide: "
        "1) Architectural breakdown and system boundaries. "
        "2) Component interactions and data contracts. "
        "3) Constraints and non-functional requirements. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "BACKEND_ENGINEER": (
        "You are the AI Backend Engineer. Analyze the architecture and provide: "
        "1) Backend implementation proposal and service structure. "
        "2) API endpoint specifications and data models. "
        "3) Persistence and error handling considerations. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "FRONTEND_ENGINEER": (
        "You are the AI Frontend Engineer. Analyze the requirements and provide: "
        "1) Frontend component hierarchy and UI layout proposal. "
        "2) Client-side state management and data fetching design. "
        "3) User interaction flows and accessibility considerations. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "QA_ENGINEER": (
        "You are the AI QA Engineer (SENTRY). Review the supplied upstream artifacts and provide: "
        "1) Comprehensive test strategy and verification matrix. "
        "2) Edge cases, failure scenarios, and boundary conditions. "
        "3) Quality risks and validation criteria. "
        "CRITICAL TRUTHFULNESS RULE: You are performing artifact review only. You MUST NOT claim "
        "tests passed or failed unless real test execution evidence was supplied to you. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "DEVOPS_ENGINEER": (
        "You are the AI DevOps Engineer. Analyze the system and provide: "
        "1) Deployment strategy and infrastructure requirements. "
        "2) Observability, logging, and health check specifications. "
        "3) Rollback plan and operational risk analysis. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT deploy, execute shell commands, or modify infra."
    ),
    "SECURITY_ENGINEER": (
        "You are the AI Security Engineer. Analyze the architecture and proposals and provide: "
        "1) Threat modeling and attack surface analysis. "
        "2) Authentication, authorization, and data isolation audit. "
        "3) Security risks and mitigation recommendations. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
    "DOCUMENTATION_ENGINEER": (
        "You are the AI Documentation Engineer. Analyze the system artifacts and provide: "
        "1) Technical documentation outline and architecture overview. "
        "2) API documentation structure. "
        "3) Operator and developer guide proposals. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files."
    ),
    "PROJECT_MANAGER": (
        "You are NEXA, the AI Project Manager. Analyze the engineering mission and provide: "
        "1) Project objectives and scope breakdown. "
        "2) Specialist work distribution and dependency ordering. "
        "3) Milestone schedule and risk analysis. "
        "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands."
    ),
}


class AgentExecutionAdapter:
    """Connects scheduled canonical WorkItem to real AI execution, producing structured

    ExecutionArtifact, marking WorkBoard completion, and passing parent artifacts to dependent
    child tasks.

    R1 IS STRICTLY READ-ONLY / ANALYSIS EXECUTION.
    SHELL=DENIED, FILESYSTEM_WRITE=DENIED, GIT_WRITE=DENIED, COMMIT=DENIED,
    PUSH=DENIED, SSH=DENIED, DEPLOY=DENIED, DB_MUTATION=DENIED, N8N_MUTATION=DENIED.
    """

    def __init__(self, workforce_service: Any, ai_client: Any = None) -> None:
        self.workforce_service = workforce_service
        self.ai_client = ai_client
        self._executing_tasks: set[str] = set()
        self._artifacts: dict[str, ExecutionArtifact] = {}
        self._artifacts_by_task: dict[str, list[ExecutionArtifact]] = {}

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | None:
        return self._artifacts.get(artifact_id)

    def get_task_artifacts(self, work_item_id: str) -> list[ExecutionArtifact]:
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
        upstream_artifacts: list[ExecutionArtifact] = []
        mission_id = work_item.metadata.get("mission_id")
        plan = self.workforce_service._plans.get(mission_id) if mission_id else None

        if plan:
            parent_ids = plan.dependency_graph.get(work_item_id, [])
            for pid in parent_ids:
                parent_arts = self.get_task_artifacts(pid)
                successful_parent = [a for a in parent_arts if a.status == "SUCCESS"]
                if successful_parent:
                    upstream_artifacts.append(successful_parent[-1])

        # Mark in-flight execution state
        self._executing_tasks.add(work_item_id)
        started_at = _now()

        # Record start activity & emit SSE event
        self.workforce_service.activity_registry.record(
            EmployeeActivity(
                employee_id=employee.employee_id,
                activity_type="EXECUTION_STARTED",
                status="EXECUTING",
                message=f"{employee.employee_name} ({employee.position_id}) started analysis for '{work_item.title}'",
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
            "R1 STRICT ENFORCEMENT: READ-ONLY ANALYSIS. Do NOT modify files or run shell commands.",
        )

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
            "Perform your role-specific read-only analysis now and return the required JSON."
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
                    message=f"{employee.employee_name} analysis failed: {str(exc)}",
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

        # Execution succeeded: create artifact
        completed_at = _now()
        self._executing_tasks.discard(work_item_id)

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
        )

        self._artifacts[artifact.artifact_id] = artifact
        self._artifacts_by_task.setdefault(work_item_id, []).append(artifact)
        work_item.artifact_id = artifact.artifact_id

        # Mark task completed on WorkBoard
        self.workforce_service.work_board.complete(employee, work_item.work_item_id)

        # Update WorkforceExecutionPlan if part of a mission
        if plan:
            plan.mark_completed(work_item.work_item_id)
            # If there is a next ready item, claim it for its assigned employee so it's ready for the next execute call
            ready_items = plan.ready_items()
            for r_id in ready_items:
                r_item = self.workforce_service.find_work_item(r_id)
                if r_item and r_item.status == "PUBLISHED" and r_item.assigned_employee_id:
                    next_emp = self.workforce_service.find_employee(r_item.assigned_employee_id)
                    if next_emp:
                        self.workforce_service.work_board.claim(next_emp, r_item.work_item_id)
                        self.workforce_service.employee_runtime.receive_work(next_emp, r_item)
                        plan.mark_running(r_item.work_item_id)
                        break

        # Record activity & emit events
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
