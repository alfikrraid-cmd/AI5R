from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for _path in (API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.agent_execution_adapter import AgentExecutionAdapter, ExecutionArtifact
from API.coding_sandbox import PatchArtifact, ReviewArtifact, RevisionAttempt, TestResult
from API.execution_ledger import ExecutionLedger, LedgerPersistenceError
from API.level_6_orchestrator import Level6MissionOrchestrator
from API.mission_lifecycle import (
    DEFAULT_MAX_REVISION_ITERATIONS,
    MAX_REVISION_ITERATIONS,
    MissionStatus,
    ReviewFinding,
)
from API.STREAMING.live_stream_api import LiveStreamAPI
from DIGITAL_EMPLOYEE.CONVERSATION.employee_conversation_store import EmployeeConversationStore
from WORKFORCE.approval_chain_runtime import (
    ApprovalChainRuntime,
    ChiefApprovalRecord,
    ChiefApprovalRequiredError,
    is_production_work_item,
    validate_chief_approval,
)
from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.digital_workforce_scheduler import DigitalWorkforceScheduler
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.it_department_operating_model import ITDepartmentOperatingModel
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization import Organization
from WORKFORCE.project_manager_capability import ProjectManagerCapability
from WORKFORCE.sprint import Sprint
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_event_bus import WorkforceEvent, WorkforceEventBus
from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


def _now() -> str:
    return datetime.now(UTC).isoformat()


POSITION_TITLES: dict[str, str] = {
    "CTO": "AI Chief Technology Officer",
    "PROJECT_MANAGER": "AI Project Manager",
    "SOLUTION_ARCHITECT": "AI Solution Architect",
    "BACKEND_ENGINEER": "AI Backend Engineer",
    "FRONTEND_ENGINEER": "AI Frontend Engineer",
    "QA_ENGINEER": "AI QA Engineer",
    "DEVOPS_ENGINEER": "AI DevOps Engineer",
    "SECURITY_ENGINEER": "AI Security Engineer",
    "DOCUMENTATION_ENGINEER": "AI Documentation Engineer",
}


class WorkforceService:
    """Canonical service managing AI5R Digital Workforce runtime and read models."""

    def __init__(
        self,
        organization_name: str = "AI5R Enterprise",
        live_stream_api: LiveStreamAPI | None = None,
        ledger: ExecutionLedger | None = None,
        auto_recover: bool = True,
    ) -> None:
        self.organization = Organization(organization_name=organization_name)
        manufactured = ITDepartmentPack().manufacture(self.organization)
        self.department = manufactured["department"]
        self.employees: list[DigitalEmployee] = manufactured["employees"]
        self._employee_by_id: dict[str, DigitalEmployee] = {
            e.employee_id: e for e in self.employees
        }
        self._employee_by_pos: dict[str, DigitalEmployee] = {
            e.position_id: e for e in self.employees
        }

        self.event_bus = WorkforceEventBus()
        self.activity_registry = EmployeeActivityRegistry(event_bus=self.event_bus)
        self.approval_chain_runtime = ApprovalChainRuntime()
        self.work_board = WorkBoard(approval_chain_runtime=self.approval_chain_runtime)
        self.employee_runtime = EmployeeRuntime(activity_registry=self.activity_registry)
        self.operating_model = ITDepartmentOperatingModel(
            employee_runtime=self.employee_runtime,
            work_board=self.work_board,
            approval_chain_runtime=self.approval_chain_runtime,
        )
        self.conversation_store = EmployeeConversationStore()
        self.live_stream_api = live_stream_api or LiveStreamAPI()
        self._missions: dict[str, dict[str, Any]] = {}
        self._plans: dict[str, WorkforceExecutionPlan] = {}
        self._sprints: dict[str, Sprint] = {}

        if ledger is not None:
            self.ledger = ledger
        elif "AI5R_EXECUTION_LEDGER_PATH" in os.environ:
            self.ledger = ExecutionLedger(os.environ["AI5R_EXECUTION_LEDGER_PATH"])
        else:
            self.ledger = None

        self.execution_adapter = AgentExecutionAdapter(
            workforce_service=self,
            ledger=self.ledger,
        )

        if self.ledger is not None and auto_recover:
            self.recover_from_ledger()

    def find_employee(self, employee_id_or_pos: str) -> DigitalEmployee | None:
        if employee_id_or_pos in self._employee_by_id:
            return self._employee_by_id[employee_id_or_pos]
        if employee_id_or_pos in self._employee_by_pos:
            return self._employee_by_pos[employee_id_or_pos]
        # Match case-insensitively
        norm = employee_id_or_pos.upper()
        if norm in self._employee_by_pos:
            return self._employee_by_pos[norm]
        for e in self.employees:
            if e.employee_id.upper() == norm or e.employee_name.upper() == norm:
                return e
        return None

    def find_employee_by_position(self, position_id: str) -> DigitalEmployee | None:
        return self._employee_by_pos.get(position_id) or self._employee_by_pos.get(position_id.upper())

    def find_work_item(self, work_item_id: str) -> WorkItem | None:
        return (
            self.work_board._published.get(work_item_id)
            or self.work_board._claimed.get(work_item_id)
            or self.work_board._completed.get(work_item_id)
            or self.work_board._released.get(work_item_id)
        )

    def _compute_employee_status(
        self, employee: DigitalEmployee
    ) -> tuple[str, dict[str, Any] | None, int]:
        if employee.status != "ACTIVE":
            return "OFFLINE", None, 0

        # Check completed production work items waiting for Chief approval
        for item in self.work_board.completed_work_items():
            if item.assigned_employee_id == employee.employee_id:
                if is_production_work_item(item) and item.metadata.get("chief_approval") is None:
                    return (
                        "WAITING_APPROVAL",
                        {
                            "task_id": item.work_item_id,
                            "title": item.title,
                            "status": "WAITING_APPROVAL",
                            "description": item.description,
                        },
                        90,
                    )

        # Check claimed (in-progress) work items
        for item in self.work_board.claimed_work_items():
            if item.assigned_employee_id == employee.employee_id:
                latest_act = self.activity_registry.latest_by_employee(employee.employee_id)
                progress = latest_act.progress if latest_act and latest_act.work_item_id == item.work_item_id else 50
                return (
                    "WORKING",
                    {
                        "task_id": item.work_item_id,
                        "title": item.title,
                        "status": item.status,
                        "description": item.description,
                    },
                    progress,
                )

        # Check runtime state from latest activity
        latest_act = self.activity_registry.latest_by_employee(employee.employee_id)
        if latest_act:
            if latest_act.status in ("THINKING", "EXECUTING", "REVIEWING", "LEARNING", "CAPABILITY_SELECTED", "WORKING"):
                return "WORKING", {"task_id": latest_act.work_item_id, "title": latest_act.message, "status": latest_act.status}, latest_act.progress
            if latest_act.status == "WAITING_APPROVAL":
                return "WAITING_APPROVAL", {"task_id": latest_act.work_item_id, "title": latest_act.message, "status": "WAITING_APPROVAL"}, latest_act.progress

        return "AVAILABLE", None, 0

    def serialize_employee(self, employee: DigitalEmployee) -> dict[str, Any]:
        pos = employee.position_id
        status, current_task, progress = self._compute_employee_status(employee)
        return {
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "position_id": pos,
            "role": POSITION_TITLES.get(pos, employee.employee_name),
            "title": POSITION_TITLES.get(pos, employee.employee_name),
            "avatar": f"/avatars/{pos.lower()}.png",
            "status": status,
            "current_task": current_task,
            "task_progress": progress,
            "skills": list(employee.capability_ids),
            "cognitive_functions": list(employee.cognitive_function_ids),
            "metadata": dict(employee.metadata),
        }

    def serialize_work_item(self, item: WorkItem) -> dict[str, Any]:
        artifact = self.get_artifact(item.artifact_id) if item.artifact_id else None
        return {
            "work_item_id": item.work_item_id,
            "task_id": item.work_item_id,
            "title": item.title,
            "description": item.description,
            "assigned_position_id": item.assigned_position_id,
            "assigned_employee_id": item.assigned_employee_id,
            "status": item.status,
            "manufacturing_order_id": item.manufacturing_order_id,
            "artifact_id": item.artifact_id,
            "artifact": artifact.to_dict() if artifact else None,
            "metadata": dict(item.metadata),
            "is_production": is_production_work_item(item),
        }

    def execute_task(self, work_item_id: str, ai_client: Any = None) -> ExecutionArtifact | PatchArtifact | ReviewArtifact:
        return self.execution_adapter.execute_work_item(work_item_id, ai_client=ai_client)

    def get_task_artifacts(self, work_item_id: str) -> list[ExecutionArtifact | PatchArtifact | ReviewArtifact]:
        return self.execution_adapter.get_task_artifacts(work_item_id)

    def get_artifact(self, artifact_id: str) -> ExecutionArtifact | PatchArtifact | ReviewArtifact | None:
        return self.execution_adapter.get_artifact(artifact_id)

    def serialize_activity(self, activity: EmployeeActivity) -> dict[str, Any]:
        return {
            "activity_id": activity.activity_id,
            "employee_id": activity.employee_id,
            "activity_type": activity.activity_type,
            "status": activity.status,
            "message": activity.message,
            "progress": activity.progress,
            "work_item_id": activity.work_item_id,
            "sprint_id": activity.sprint_id,
            "mission_id": activity.mission_id,
            "updated_at": activity.updated_at,
            "metadata": dict(activity.metadata),
        }

    def list_employees(self) -> list[dict[str, Any]]:
        return [self.serialize_employee(e) for e in self.employees]

    def get_employee(self, employee_id: str) -> dict[str, Any] | None:
        employee = self.find_employee(employee_id)
        if employee is None:
            return None
        data = self.serialize_employee(employee)
        acts = self.activity_registry.list_by_employee(employee.employee_id)
        data["activities"] = [
            self.serialize_activity(a)
            for a in sorted(acts, key=lambda a: a.updated_at, reverse=True)[:10]
        ]
        return data

    def get_board(self) -> dict[str, Any]:
        published = [self.serialize_work_item(i) for i in self.work_board.available_work_items()]
        claimed = [self.serialize_work_item(i) for i in self.work_board.claimed_work_items()]
        completed = [self.serialize_work_item(i) for i in self.work_board.completed_work_items()]
        released = [self.serialize_work_item(i) for i in self.work_board.released_work_items()]
        return {
            "published": published,
            "claimed": claimed,
            "completed": completed,
            "released": released,
            "summary": {
                "total_items": len(published) + len(claimed) + len(completed) + len(released),
                "published_count": len(published),
                "claimed_count": len(claimed),
                "completed_count": len(completed),
                "released_count": len(released),
            },
        }

    def list_activities(
        self, employee_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        if employee_id:
            acts = self.activity_registry.list_by_employee(employee_id)
        else:
            acts = self.activity_registry.list_all()

        sorted_acts = sorted(acts, key=lambda a: a.updated_at, reverse=True)
        return [self.serialize_activity(a) for a in sorted_acts[:limit]]

    def get_metrics(self) -> dict[str, Any]:
        employees_data = self.list_employees()
        status_counts: dict[str, int] = {}
        for emp in employees_data:
            st = emp["status"]
            status_counts[st] = status_counts.get(st, 0) + 1

        published = self.work_board.available_work_items()
        claimed = self.work_board.claimed_work_items()
        completed = self.work_board.completed_work_items()
        released = self.work_board.released_work_items()

        pending_approvals = sum(
            1
            for item in completed
            if is_production_work_item(item) and item.metadata.get("chief_approval") is None
        )

        return {
            "status": "OK",
            "total_employees": len(self.employees),
            "active_employees": sum(1 for e in self.employees if e.status == "ACTIVE"),
            "available_employees": status_counts.get("AVAILABLE", 0),
            "working_employees": status_counts.get("WORKING", 0),
            "waiting_approval_employees": status_counts.get("WAITING_APPROVAL", 0),
            "offline_employees": status_counts.get("OFFLINE", 0),
            "total_tasks": len(published) + len(claimed) + len(completed) + len(released),
            "published_tasks": len(published),
            "in_progress_tasks": len(claimed),
            "completed_tasks": len(completed),
            "released_tasks": len(released),
            "pending_approvals": pending_approvals,
            "uptime": "OPERATIONAL",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def assign_task(
        self,
        title: str,
        description: str = "",
        position_id: str | None = None,
        employee_id: str | None = None,
        is_production: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta = dict(metadata or {})
        if is_production:
            meta["is_production"] = True

        target_employee: DigitalEmployee | None = None
        if employee_id:
            target_employee = self.find_employee(employee_id)
            if target_employee is None:
                raise KeyError(f"Employee not found: {employee_id}")
            target_position_id = target_employee.position_id
        elif position_id:
            target_position_id = position_id
            target_employee = self.find_employee_by_position(position_id)
        else:
            target_position_id = "PROJECT_MANAGER"
            target_employee = self.find_employee_by_position("PROJECT_MANAGER")

        work_item = WorkItem(
            title=title,
            description=description,
            assigned_position_id=target_position_id,
            metadata=meta,
        )
        self.work_board.publish(work_item)

        if target_employee is not None:
            self.work_board.claim(target_employee, work_item.work_item_id)
            self.employee_runtime.receive_work(target_employee, work_item)

        if self.ledger is not None:
            self.ledger.record_work_item({
                "work_item_id": work_item.work_item_id,
                "mission_id": meta.get("mission_id"),
                "title": work_item.title,
                "description": work_item.description,
                "assigned_position_id": work_item.assigned_position_id,
                "assigned_employee_id": work_item.assigned_employee_id,
                "status": work_item.status,
                "is_production": is_production_work_item(work_item),
                "manufacturing_order_id": work_item.manufacturing_order_id,
                "artifact_id": work_item.artifact_id,
                "dependencies": [],
                "recovery_status": None,
                "metadata": work_item.metadata,
            })

        self.live_stream_api.publish(
            event_type="WORKFORCE_TASK_ASSIGNED",
            payload={
                "work_item_id": work_item.work_item_id,
                "title": work_item.title,
                "assigned_position_id": work_item.assigned_position_id,
                "assigned_employee_id": work_item.assigned_employee_id,
                "is_production": is_production_work_item(work_item),
            },
        )

        return {
            "status": "ASSIGNED",
            "work_item": self.serialize_work_item(work_item),
        }

    def chat(
        self,
        employee_id: str,
        message: str,
        conversation_id: str | None = None,
        ai_client: Any = None,
    ) -> dict[str, Any]:
        employee = self.find_employee(employee_id)
        if employee is None:
            raise KeyError(f"Employee not found: {employee_id}")

        if conversation_id:
            conversation = self.conversation_store.get(conversation_id)
            if conversation is None:
                conversation = self.conversation_store.create(
                    employee_id=employee.employee_id,
                    title=f"Chat with {employee.employee_name}",
                )
        else:
            conversation = self.conversation_store.create(
                employee_id=employee.employee_id,
                title=f"Chat with {employee.employee_name}",
            )

        conversation.add_message("user", message)

        response_text = None
        if ai_client is not None:
            try:
                system_prompt = (
                    f"You are {employee.employee_name}, serving as {employee.position_id} in the AI5R Digital Workforce. "
                    f"Your skills are {', '.join(employee.capability_ids)}. "
                    "Respond helpfully, concisely, and professionally."
                )
                response_text = ai_client.generate(
                    prompt=message,
                    system_prompt=system_prompt,
                    capability="chat",
                )
            except Exception:
                response_text = None

        if not response_text:
            response_text = (
                f"[{employee.employee_name}] Received instructions: \"{message}\". "
                f"Assigned to {employee.position_id} (Capabilities: {', '.join(employee.capability_ids)})."
            )

        conversation.add_message(
            "assistant",
            response_text,
            metadata={"employee_id": employee.employee_id, "position_id": employee.position_id},
        )

        self.live_stream_api.publish(
            event_type="WORKFORCE_CHAT_MESSAGE",
            payload={
                "conversation_id": conversation.conversation_id,
                "employee_id": employee.employee_id,
                "role": "assistant",
                "content": response_text,
            },
        )

        return {
            "status": "OK",
            "conversation_id": conversation.conversation_id,
            "employee_id": employee.employee_id,
            "response": response_text,
            "messages": list(conversation.messages),
        }

    def release_task(self, work_item_id: str, approval: Any = None) -> WorkItem:
        """Release a completed work item, requiring Chief approval if production-impacting."""
        item = self.find_work_item(work_item_id)
        if item and is_production_work_item(item):
            resolved_approval = approval or self.approval_chain_runtime.get_chief_approval(work_item_id)
            if resolved_approval and self.ledger is not None:
                self.ledger.record_chief_approval(
                    approval_id=getattr(resolved_approval, "approval_id", f"CHIEF-APPR-{uuid4().hex[:8].upper()}"),
                    work_item_id=work_item_id,
                    approver_id=getattr(resolved_approval, "approver_id", "raid"),
                    approver_role=getattr(resolved_approval, "approver_role", "CHIEF_ARCHITECT"),
                    is_human=getattr(resolved_approval, "is_human", True),
                    status=getattr(resolved_approval, "status", "APPROVED"),
                    scope=getattr(resolved_approval, "scope", "PRODUCTION_DEPLOYMENT"),
                    approved_at=getattr(resolved_approval, "approved_at", datetime.now(UTC).isoformat()),
                    metadata=getattr(resolved_approval, "metadata", {}),
                )

        prev_status = item.status if item else "COMPLETED"
        prev_metadata = dict(item.metadata) if item else {}

        released = self.operating_model.release(work_item_id, approval=approval)
        if self.ledger is not None:
            try:
                self.ledger.update_work_item_status(
                    work_item_id=work_item_id,
                    status="RELEASED",
                    metadata_update={"chief_approval": released.metadata.get("chief_approval")},
                )
            except Exception as exc:
                if work_item_id in self.work_board._released:
                    rel_item = self.work_board._released.pop(work_item_id)
                    rel_item.status = prev_status
                    rel_item.metadata = prev_metadata
                    self.work_board._completed[work_item_id] = rel_item
                raise LedgerPersistenceError(
                    f"Production release persistence failed for work item '{work_item_id}'. In-memory release rolled back to COMPLETED."
                ) from exc
        return released

    def create_mission(
        self,
        title: str,
        description: str = "",
        is_production: bool = False,
        metadata: dict[str, Any] | None = None,
        include_security: bool = False,
        max_iterations: int | None = None,
    ) -> dict[str, Any]:
        pm = self.find_employee_by_position("PROJECT_MANAGER")
        if pm is None:
            raise KeyError("PROJECT_MANAGER employee not found")

        meta = dict(metadata or {})
        mission_id = f"MISSION-{uuid4().hex[:12].upper()}"
        include_security = bool(include_security or meta.get("include_security") or meta.get("level") == 6)
        created_by = meta.get("created_by", "CHIEF")
        effective_max_iterations = int(max_iterations or meta.get("max_iterations") or DEFAULT_MAX_REVISION_ITERATIONS)
        meta["max_iterations"] = effective_max_iterations
        meta["include_security"] = include_security

        sprint = Sprint(
            objective=title,
            organization_id=self.organization.organization_id,
            department_id=self.department.department_id,
            metadata={
                "mission_id": mission_id,
                "is_production": is_production,
                "include_security": include_security,
                **meta,
            },
        )

        pm_cap = ProjectManagerCapability()
        breakdown_result = pm_cap.breakdown_sprint(pm, sprint)
        tasks: list[WorkItem] = breakdown_result["tasks"]

        # Tag tasks with mission info and guard production deployment
        for task in tasks:
            task.metadata["mission_id"] = mission_id
            task.metadata["sprint_id"] = sprint.sprint_id
            if description:
                task.description = f"{task.description}\n\nMission: {description}".strip() if task.description else f"Mission: {description}"
            if is_production and task.assigned_position_id == "DEVOPS_ENGINEER":
                task.metadata["is_production"] = True
                task.metadata["requires_chief_approval"] = True
            elif is_production:
                task.metadata["mission_is_production"] = True

        pm_cap.assign_tasks(pm, tasks, self.employees)

        # Build canonical dependency graph
        tasks_by_pos = {t.assigned_position_id: t for t in tasks}
        arch_task = tasks_by_pos.get("SOLUTION_ARCHITECT")
        backend_task = tasks_by_pos.get("BACKEND_ENGINEER")
        frontend_task = tasks_by_pos.get("FRONTEND_ENGINEER")
        qa_task = tasks_by_pos.get("QA_ENGINEER")
        sec_task = tasks_by_pos.get("SECURITY_ENGINEER")
        devops_task = tasks_by_pos.get("DEVOPS_ENGINEER")
        doc_task = tasks_by_pos.get("DOCUMENTATION_ENGINEER")

        deps_map: dict[str, list[str]] = {}
        if arch_task:
            deps_map[arch_task.work_item_id] = []
        if backend_task and arch_task:
            deps_map[backend_task.work_item_id] = [arch_task.work_item_id]
        if frontend_task and arch_task:
            deps_map[frontend_task.work_item_id] = [arch_task.work_item_id]
        if qa_task:
            qa_deps = []
            if backend_task:
                qa_deps.append(backend_task.work_item_id)
            if frontend_task:
                qa_deps.append(frontend_task.work_item_id)
            deps_map[qa_task.work_item_id] = qa_deps
        if sec_task:
            sec_deps = []
            if qa_task:
                sec_deps.append(qa_task.work_item_id)
            elif backend_task:
                sec_deps.append(backend_task.work_item_id)
            deps_map[sec_task.work_item_id] = sec_deps
        if devops_task:
            if sec_task:
                deps_map[devops_task.work_item_id] = [sec_task.work_item_id]
            elif qa_task:
                deps_map[devops_task.work_item_id] = [qa_task.work_item_id]
        if doc_task and qa_task:
            deps_map[doc_task.work_item_id] = [qa_task.work_item_id]

        plan = WorkforceExecutionPlan(mission_id=mission_id)
        for task in tasks:
            plan.add_work_item(task.work_item_id, dependencies=deps_map.get(task.work_item_id, []))

        scheduler = DigitalWorkforceScheduler()
        decision = scheduler.next_work_item(plan)

        # Publish all tasks to the shared work board and claim the initial ready task
        for task in tasks:
            self.work_board.publish(task)
            if decision.work_item_id and task.work_item_id == decision.work_item_id:
                assigned_emp = self.find_employee(task.assigned_employee_id)
                if assigned_emp:
                    self.work_board.claim(assigned_emp, task.work_item_id)
                    self.employee_runtime.receive_work(assigned_emp, task)

        self.activity_registry.record(
            EmployeeActivity(
                employee_id=pm.employee_id,
                activity_type="MISSION_DELEGATED",
                status="ACTIVE",
                message=f"Decomposed mission '{title}' into {len(tasks)} specialist work items",
                progress=10,
                work_item_id=decision.work_item_id or "",
                sprint_id=sprint.sprint_id,
                mission_id=mission_id,
            )
        )

        mission_data = {
            "mission_id": mission_id,
            "title": title,
            "objective": title,
            "description": description,
            "is_production": is_production,
            "status": "IN_PROGRESS",
            "created_by": created_by,
            "current_iteration": 0,
            "max_iterations": max_iterations,
            "approval_status": "PENDING",
            "execution_worktree": str(REPO_ROOT),
            "sprint_id": sprint.sprint_id,
            "plan_id": plan.plan_id,
            "project_manager_id": pm.employee_id,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "task_ids": [t.work_item_id for t in tasks],
            "metadata": meta,
        }

        self._missions[mission_id] = mission_data
        self._plans[mission_id] = plan
        self._sprints[mission_id] = sprint

        if self.ledger is not None:
            serialized_tasks = []
            for t in tasks:
                serialized_tasks.append({
                    "work_item_id": t.work_item_id,
                    "mission_id": mission_id,
                    "title": t.title,
                    "description": t.description,
                    "assigned_position_id": t.assigned_position_id,
                    "assigned_employee_id": t.assigned_employee_id,
                    "status": t.status,
                    "is_production": is_production_work_item(t),
                    "manufacturing_order_id": t.manufacturing_order_id,
                    "artifact_id": t.artifact_id,
                    "dependencies": deps_map.get(t.work_item_id, []),
                    "recovery_status": None,
                    "metadata": t.metadata,
                })

            sprint_dict = {
                "sprint_id": sprint.sprint_id,
                "mission_id": mission_id,
                "objective": sprint.objective,
                "organization_id": sprint.organization_id,
                "department_id": sprint.department_id,
                "status": sprint.status,
                "assigned_employee_ids": sprint.assigned_employee_ids,
                "task_ids": sprint.task_ids,
                "metadata": sprint.metadata,
                "created_at": mission_data["created_at"],
            }

            self.ledger.record_mission_bundle(
                mission_dict=mission_data,
                sprint_dict=sprint_dict,
                plan_dict=plan.snapshot(),
                work_items=serialized_tasks,
            )

            try:
                self.ledger.record_event(
                    event_type="MISSION_CREATED",
                    who=created_by,
                    what=f"Mission '{title}' created with {len(tasks)} tasks",
                    employee_id=pm.employee_id,
                    role="PROJECT_MANAGER",
                    mission_id=mission_id,
                    why="Mission delegated to NEXA",
                    result="IN_PROGRESS",
                    metadata={"title": title, "tasks_count": len(tasks), "is_production": is_production},
                )
                self.ledger.record_event(
                    event_type="PLAN_CREATED",
                    who="NEXA (PROJECT_MANAGER)",
                    what=f"Execution plan '{plan.plan_id}' constructed with dependency graph",
                    employee_id=pm.employee_id,
                    role="PROJECT_MANAGER",
                    mission_id=mission_id,
                    why="Structured task decomposition and DAG scheduling",
                    result="PLAN_CREATED",
                    metadata={"plan_id": plan.plan_id, "dependency_graph": deps_map},
                )
            except Exception:
                pass

        self.live_stream_api.publish(
            event_type="WORKFORCE_MISSION_CREATED",
            payload={
                "mission_id": mission_id,
                "title": title,
                "tasks_count": len(tasks),
                "plan_id": plan.plan_id,
                "is_production": is_production,
            },
        )

        return self.get_mission(mission_id)

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        mission = self._missions.get(mission_id)
        if not mission:
            return None

        plan = self._plans.get(mission_id)
        task_ids = mission.get("task_ids", [])
        tasks = []
        completed_count = 0

        for tid in task_ids:
            item = self.find_work_item(tid)
            if item:
                serialized = self.serialize_work_item(item)
                emp = self.find_employee(item.assigned_employee_id) if item.assigned_employee_id else None
                serialized["assigned_employee_name"] = emp.employee_name if emp else None
                serialized["dependencies"] = plan.dependency_graph.get(tid, []) if plan else []
                tasks.append(serialized)
                if item.status in ("COMPLETED", "RELEASED"):
                    completed_count += 1
                    if plan and tid not in plan.completed:
                        plan.mark_completed(tid)
                elif item.status == "CLAIMED":
                    if plan and tid not in plan.running:
                        plan.mark_running(tid)

        total_tasks = len(tasks)
        progress = int((completed_count / total_tasks) * 100) if total_tasks > 0 else 0

        canonical_status = mission.get("status", "IN_PROGRESS")
        if canonical_status not in (
            MissionStatus.READY_FOR_CHIEF_APPROVAL,
            MissionStatus.APPROVED,
            MissionStatus.REVISION_REQUIRED,
            MissionStatus.REVISING,
            MissionStatus.RE_REVIEWING,
            MissionStatus.REVISION_LIMIT_REACHED,
            MissionStatus.BLOCKED,
            MissionStatus.FAILED,
            MissionStatus.CANCELLED,
            MissionStatus.COMPLETED,
        ):
            if total_tasks > 0 and completed_count == total_tasks:
                canonical_status = "COMPLETED"
            elif completed_count > 0:
                canonical_status = "IN_PROGRESS"

        assignments = []
        for t in tasks:
            assignments.append({
                "task_id": t["work_item_id"],
                "employee_id": t.get("assigned_employee_id"),
                "employee_name": t.get("assigned_employee_name"),
                "position_id": t.get("assigned_position_id"),
                "status": t.get("status"),
            })

        return {
            "mission_id": mission["mission_id"],
            "title": mission["title"],
            "objective": mission.get("objective") or mission["title"],
            "description": mission.get("description", ""),
            "is_production": mission.get("is_production", False),
            "status": canonical_status,
            "created_by": mission.get("created_by", "CHIEF"),
            "assigned_employees": [t.get("assigned_employee_id") for t in tasks if t.get("assigned_employee_id")],
            "progress": progress,
            "sprint_id": mission.get("sprint_id"),
            "plan_id": mission.get("plan_id"),
            "project_manager_id": mission.get("project_manager_id"),
            "current_iteration": mission.get("current_iteration", 0),
            "max_iterations": mission.get("max_iterations", DEFAULT_MAX_REVISION_ITERATIONS),
            "execution_worktree": mission.get("execution_worktree", str(REPO_ROOT)),
            "latest_review_result": mission.get("latest_review_result"),
            "latest_security_review_result": mission.get("latest_security_review_result"),
            "approval_status": mission.get("approval_status", "PENDING"),
            "created_at": mission.get("created_at"),
            "updated_at": mission.get("updated_at"),
            "completed_at": mission.get("completed_at"),
            "tasks": tasks,
            "assignments": assignments,
            "execution_plan": plan.snapshot() if plan else {},
            "task_graph": plan.dependency_graph if plan else {},
            "findings": self.get_mission_findings(mission_id),
            "metadata": dict(mission.get("metadata", {})),
        }

    def _persist_mission_state(
        self,
        mission_id: str,
        status: str,
        metadata_update: dict[str, Any] | None = None,
    ) -> None:
        """Atomically persist mission status to in-memory store and SQLite ledger."""
        mission = self._missions.get(mission_id)
        if mission:
            mission["status"] = status
            mission["updated_at"] = _now()
            if metadata_update:
                mission.setdefault("metadata", {}).update(metadata_update)

        if self.ledger is not None:
            try:
                self.ledger.update_mission_status(
                    mission_id=mission_id,
                    status=status,
                    updated_at=_now(),
                    metadata_update=metadata_update,
                )
            except Exception:
                pass

    def orchestrate_mission(
        self,
        mission_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
        security_client: Any = None,
        max_steps: int = 50,
    ) -> dict[str, Any]:
        """Run the governed Level 6 autonomous revision loop for a mission."""
        orchestrator = Level6MissionOrchestrator(self)
        return orchestrator.orchestrate(
            mission_id=mission_id,
            ai_client=ai_client,
            sentry_client=sentry_client,
            security_client=security_client,
            max_steps=max_steps,
        )

    def get_mission_findings(self, mission_id: str) -> list[dict[str, Any]]:
        """Get all review findings for a mission."""
        if self.ledger is not None:
            try:
                return self.ledger.load_findings(mission_id=mission_id)
            except Exception:
                pass
        return self._missions.get(mission_id, {}).get("findings", [])

    def get_mission_events(self, mission_id: str) -> list[dict[str, Any]]:
        """Get ordered lifecycle events for a mission."""
        if self.ledger is not None:
            try:
                return self.ledger.load_events(mission_id=mission_id)
            except Exception:
                pass
        return [
            a.to_dict() if hasattr(a, "to_dict") else a
            for a in self.activity_registry.list_all()
            if getattr(a, "mission_id", None) == mission_id
        ]

    def approve_mission(
        self,
        mission_id: str,
        approver_id: str = "raid",
        approver_role: str = "CHIEF_ARCHITECT",
        is_human: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Human Chief explicit approval gate for mission completion/release."""
        if not is_human:
            raise ChiefApprovalRequiredError("Human Chief approval is required. Autonomous/AI approval is strictly forbidden.")

        mission = self._missions.get(mission_id)
        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found")

        curr_status = mission.get("status")
        if curr_status != MissionStatus.READY_FOR_CHIEF_APPROVAL:
            raise ValueError(
                f"Cannot approve mission in state '{curr_status}'. Mission must be in READY_FOR_CHIEF_APPROVAL state."
            )

        now_str = _now()
        mission["status"] = MissionStatus.APPROVED
        mission["approval_status"] = "APPROVED"
        mission["completed_at"] = now_str
        meta = metadata or {}
        mission.setdefault("metadata", {}).update(meta)
        mission["metadata"]["approved_by"] = approver_id
        mission["metadata"]["approver_role"] = approver_role
        mission["metadata"]["approved_at"] = now_str

        self._persist_mission_state(mission_id, MissionStatus.APPROVED, metadata_update={
            "approval_status": "APPROVED",
            "completed_at": now_str,
            "approved_by": approver_id,
        })

        if self.ledger is not None:
            try:
                self.ledger.record_event(
                    event_type="CHIEF_APPROVED",
                    who=f"{approver_role} ({approver_id})",
                    what=f"Human Chief approved mission '{mission['title']}'",
                    employee_id=approver_id,
                    role=approver_role,
                    mission_id=mission_id,
                    why="Chief verification satisfied",
                    result="APPROVED",
                    metadata={"approver_id": approver_id, "approver_role": approver_role, "is_human": is_human},
                )
                self.ledger.record_event(
                    event_type="MISSION_COMPLETED",
                    who="SYSTEM",
                    what=f"Mission '{mission['title']}' completed successfully following Chief approval",
                    mission_id=mission_id,
                    result="COMPLETED",
                )
            except Exception:
                pass

        mission["status"] = MissionStatus.COMPLETED
        self._persist_mission_state(mission_id, MissionStatus.COMPLETED)
        return self.get_mission(mission_id)

    def reject_mission(
        self,
        mission_id: str,
        approver_id: str = "raid",
        approver_role: str = "CHIEF_ARCHITECT",
        reason: str = "",
    ) -> dict[str, Any]:
        """Human Chief rejection of mission."""
        mission = self._missions.get(mission_id)
        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found")

        mission["status"] = MissionStatus.CANCELLED
        mission["approval_status"] = "REJECTED"
        mission.setdefault("metadata", {})["rejection_reason"] = reason
        self._persist_mission_state(mission_id, MissionStatus.CANCELLED)

        if self.ledger is not None:
            try:
                self.ledger.record_event(
                    event_type="CHIEF_REJECTED",
                    who=f"{approver_role} ({approver_id})",
                    what=f"Chief rejected mission '{mission['title']}': {reason}",
                    mission_id=mission_id,
                    result="REJECTED",
                )
            except Exception:
                pass
        return self.get_mission(mission_id)

    def cancel_mission(self, mission_id: str, reason: str = "") -> dict[str, Any]:
        """Cancel an in-progress mission."""
        mission = self._missions.get(mission_id)
        if not mission:
            raise KeyError(f"Mission '{mission_id}' not found")

        mission["status"] = MissionStatus.CANCELLED
        mission.setdefault("metadata", {})["cancellation_reason"] = reason
        self._persist_mission_state(mission_id, MissionStatus.CANCELLED)

        if self.ledger is not None:
            try:
                self.ledger.record_event(
                    event_type="MISSION_CANCELLED",
                    who="USER",
                    what=f"Mission cancelled: {reason}",
                    mission_id=mission_id,
                    result="CANCELLED",
                )
            except Exception:
                pass
        return self.get_mission(mission_id)

    def list_missions(self) -> list[dict[str, Any]]:
        return [self.get_mission(mid) for mid in self._missions if self.get_mission(mid) is not None]

    def grant_chief_approval(
        self,
        work_item_id: str,
        approver_id: str = "raid",
        approver_role: str = "CHIEF_ARCHITECT",
        is_human: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChiefApprovalRecord:
        """Grant human Chief approval for a work item, recording to runtime and ledger."""
        record = self.approval_chain_runtime.grant_chief_approval(
            work_item_id=work_item_id,
            approver_id=approver_id,
            approver_role=approver_role,
            is_human=is_human,
            metadata=metadata,
        )
        if self.ledger is not None:
            try:
                self.ledger.record_chief_approval(
                    approval_id=record.approval_id,
                    work_item_id=record.work_item_id,
                    approver_id=record.approver_id,
                    approver_role=record.approver_role,
                    is_human=record.is_human,
                    status=record.status,
                    scope=record.scope,
                    approved_at=record.approved_at,
                    metadata=record.metadata,
                )
            except Exception as exc:
                self.approval_chain_runtime._chief_approvals.pop(work_item_id, None)
                raise LedgerPersistenceError(
                    f"Chief approval persistence failed for work item '{work_item_id}'. In-memory approval rolled back."
                ) from exc
        return record

    def recover_from_ledger(self) -> None:
        """Rehydrate state from persistent ExecutionLedger without replaying side effects."""
        if self.ledger is None:
            return

        # 1. Sprints
        for s in self.ledger.load_sprints():
            sprint = Sprint(
                objective=s["objective"],
                organization_id=s["organization_id"],
                department_id=s["department_id"],
                status=s["status"],
                assigned_employee_ids=s["assigned_employee_ids"],
                task_ids=s["task_ids"],
                metadata=s["metadata"],
                sprint_id=s["sprint_id"],
            )
            self._sprints[s["mission_id"]] = sprint

        # 2. Plans
        for p in self.ledger.load_plans():
            plan = WorkforceExecutionPlan(
                mission_id=p["mission_id"],
                work_queue=p["work_queue"],
                dependency_graph=p["dependency_graph"],
                running=p["running"],
                waiting=p["waiting"],
                blocked=p["blocked"],
                completed=p["completed"],
                metadata=p["metadata"],
                plan_id=p["plan_id"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
            )
            self._plans[p["mission_id"]] = plan

        # 3. Missions
        for m in self.ledger.load_missions():
            self._missions[m["mission_id"]] = m

        # 4. Work Items & WorkBoard (idempotent reset)
        self.work_board._published.clear()
        self.work_board._claimed.clear()
        self.work_board._completed.clear()
        self.work_board._released.clear()

        for wi in self.ledger.load_work_items():
            item = WorkItem(
                title=wi["title"],
                assigned_position_id=wi["assigned_position_id"],
                description=wi["description"],
                status=wi["status"],
                assigned_employee_id=wi["assigned_employee_id"],
                manufacturing_order_id=wi["manufacturing_order_id"],
                artifact_id=wi["artifact_id"],
                metadata=wi["metadata"],
                work_item_id=wi["work_item_id"],
            )
            if wi.get("recovery_status"):
                item.metadata["recovery_status"] = wi["recovery_status"]

            st = item.status
            if st == "CLAIMED":
                self.work_board._claimed[item.work_item_id] = item
            elif st == "COMPLETED":
                self.work_board._completed[item.work_item_id] = item
            elif st == "RELEASED":
                self.work_board._released[item.work_item_id] = item
            else:
                self.work_board._published[item.work_item_id] = item

            mid = wi.get("mission_id")
            if mid and mid in self._sprints:
                self._sprints[mid].add_work_item(item)

        # 5. Chief Approvals
        self.approval_chain_runtime._chief_approvals.clear()
        for ca in self.ledger.load_chief_approvals():
            record = ChiefApprovalRecord(
                work_item_id=ca["work_item_id"],
                approver_id=ca["approver_id"],
                approver_role=ca["approver_role"],
                is_human=ca["is_human"],
                status=ca["status"],
                approval_id=ca["approval_id"],
                approved_at=ca["approved_at"],
                scope=ca["scope"],
                metadata=ca["metadata"],
            )
            self.approval_chain_runtime._chief_approvals[ca["work_item_id"]] = record

        # 6. Artifacts
        self.execution_adapter._artifacts.clear()
        self.execution_adapter._artifacts_by_task.clear()
        for art in self.ledger.load_artifacts():
            payload = art["payload"]
            art_type = art["artifact_type"]
            if art_type == "PATCH":
                test_results = [
                    TestResult(
                        test_result_id=tr["test_result_id"],
                        command_id=tr["command_id"],
                        target=tr["target"],
                        exit_code=tr["exit_code"],
                        passed=tr["passed"],
                        duration=tr["duration"],
                        stdout_summary=tr["stdout_summary"],
                        stderr_summary=tr["stderr_summary"],
                        timed_out=tr["timed_out"],
                    )
                    for tr in art.get("test_results", [])
                ]
                obj = PatchArtifact(
                    artifact_id=art["artifact_id"],
                    work_item_id=art["work_item_id"],
                    employee_id=art["employee_id"],
                    role=art["role"],
                    sandbox_id=payload.get("sandbox_id", ""),
                    base_commit=payload.get("base_commit", ""),
                    summary=art["summary"],
                    changed_files=payload.get("changed_files", []),
                    diff_stat=payload.get("diff_stat", ""),
                    git_diff=payload.get("git_diff", ""),
                    tests_requested=payload.get("tests_requested", []),
                    tests_executed=payload.get("tests_executed", []),
                    test_results=test_results,
                    started_at=payload.get("started_at", art["created_at"]),
                    completed_at=payload.get("completed_at", art["created_at"]),
                    status=art["status"],
                    provider_metadata=payload.get("provider_metadata", {}),
                    error=payload.get("error"),
                    metadata=payload.get("metadata", {}),
                )
            elif art_type == "REVIEW":
                obj = ReviewArtifact(
                    review_id=art["artifact_id"],
                    work_item_id=art["work_item_id"],
                    employee_id=art["employee_id"],
                    role=art["role"],
                    reviewed_artifact_ids=art["parent_artifact_ids"],
                    decision=payload.get("decision", "APPROVE_TECHNICAL"),
                    findings=payload.get("findings", []),
                    risks=payload.get("risks", []),
                    test_evidence_reviewed=payload.get("test_evidence_reviewed", {}),
                    recommended_action=payload.get("recommended_action", ""),
                    started_at=payload.get("started_at", art["created_at"]),
                    completed_at=payload.get("completed_at", art["created_at"]),
                    status=art["status"],
                    provider_metadata=payload.get("provider_metadata", {}),
                    metadata=payload.get("metadata", {}),
                )
            else:
                obj = ExecutionArtifact(
                    artifact_id=art["artifact_id"],
                    work_item_id=art["work_item_id"],
                    employee_id=art["employee_id"],
                    role=art["role"],
                    status=art["status"],
                    summary=art["summary"],
                    output=payload.get("output", {}),
                    started_at=payload.get("started_at", art["created_at"]),
                    completed_at=payload.get("completed_at", art["created_at"]),
                    provider_metadata=payload.get("provider_metadata", {}),
                    error=payload.get("error"),
                    metadata=payload.get("metadata", {}),
                )
            self.execution_adapter._artifacts[obj.artifact_id] = obj
            self.execution_adapter._artifacts_by_task.setdefault(obj.work_item_id, []).append(obj)

        # 7. Revisions
        self.execution_adapter._revisions.clear()
        self.execution_adapter._revisions_by_task.clear()
        for rev in self.ledger.load_revisions():
            rev_obj = RevisionAttempt(
                revision_id=rev["revision_id"],
                work_item_id=rev["work_item_id"],
                employee_id=rev["employee_id"],
                role=rev["role"],
                attempt_number=rev["attempt_number"],
                parent_patch_artifact_id=rev["parent_patch_artifact_id"],
                trigger_review_id=rev["trigger_review_id"],
                status=rev["status"],
                created_at=rev["created_at"],
                started_at=rev["started_at"],
                completed_at=rev["completed_at"],
                error=rev["error"],
                metadata=rev["metadata"],
            )
            self.execution_adapter._revisions[rev_obj.revision_id] = rev_obj
            self.execution_adapter._revisions_by_task.setdefault(rev_obj.work_item_id, []).append(rev_obj)

        # 8. In-flight recovery (Crashed process recovery without side effect replay)
        in_flight = self.ledger.get_in_flight_executions()
        for inf in in_flight:
            w_id = inf["work_item_id"]
            item = self.find_work_item(w_id)
            if item:
                item.metadata["recovery_status"] = "RECOVERY_REQUIRED"
                if item.work_item_id not in self.work_board._claimed:
                    self.work_board._claimed[item.work_item_id] = item
                    self.work_board._published.pop(item.work_item_id, None)
                self.ledger.update_work_item_status(
                    work_item_id=w_id,
                    status="CLAIMED",
                    recovery_status="RECOVERY_REQUIRED",
                    metadata_update={"recovery_status": "RECOVERY_REQUIRED"},
                )
                self.activity_registry.record(
                    EmployeeActivity(
                        employee_id=inf["employee_id"],
                        activity_type="EXECUTION_RECOVERED",
                        status="CLAIMED",
                        message=f"Recovered in-flight execution for '{item.title}' after restart. Status set to RECOVERY_REQUIRED. Side effects were not replayed.",
                        progress=0,
                        work_item_id=w_id,
                        metadata={"execution_id": inf["execution_id"], "recovery_status": "RECOVERY_REQUIRED"},
                    )
                )

        in_flight_revs = self.ledger.get_in_flight_revisions()
        for ifr in in_flight_revs:
            w_id = ifr["work_item_id"]
            rev_id = ifr["revision_id"]
            item = self.find_work_item(w_id)
            if item:
                item.metadata["recovery_status"] = "RECOVERY_REQUIRED"
                if item.work_item_id not in self.work_board._claimed:
                    self.work_board._claimed[item.work_item_id] = item
                    self.work_board._published.pop(item.work_item_id, None)
                self.ledger.update_revision_status(
                    revision_id=rev_id,
                    status="RECOVERY_REQUIRED",
                )
                self.ledger.update_work_item_status(
                    work_item_id=w_id,
                    status="CLAIMED",
                    recovery_status="RECOVERY_REQUIRED",
                    metadata_update={"recovery_status": "RECOVERY_REQUIRED"},
                )
                if rev_id in self.execution_adapter._revisions:
                    self.execution_adapter._revisions[rev_id].status = "RECOVERY_REQUIRED"

                self.live_stream_api.publish(
                    event_type="revision_recovery_required",
                    payload={
                        "work_item_id": w_id,
                        "revision_id": rev_id,
                        "status": "RECOVERY_REQUIRED",
                        "side_effects_replayed": False,
                    },
                )
                self.activity_registry.record(
                    EmployeeActivity(
                        employee_id=ifr["employee_id"],
                        activity_type="REVISION_RECOVERED",
                        status="CLAIMED",
                        message=f"Recovered in-flight revision for '{item.title}' after restart. Status set to RECOVERY_REQUIRED. Side effects were not replayed.",
                        progress=0,
                        work_item_id=w_id,
                        metadata={"revision_id": rev_id, "recovery_status": "RECOVERY_REQUIRED"},
                    )
                )

    def execute_revision(
        self,
        work_item_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
    ) -> dict[str, Any]:
        """Execute one bounded autonomous revision cycle."""
        return self.execution_adapter.execute_revision(
            work_item_id=work_item_id,
            ai_client=ai_client,
            sentry_client=sentry_client,
        )

    def execute_revision_cycle(
        self,
        work_item_id: str,
        ai_client: Any = None,
        sentry_client: Any = None,
    ) -> dict[str, Any]:
        """Execute the full bounded autonomous revision loop up to MAX_AUTOMATIC_REVISIONS."""
        return self.execution_adapter.execute_revision_cycle(
            work_item_id=work_item_id,
            ai_client=ai_client,
            sentry_client=sentry_client,
        )

    def get_task_revisions(self, work_item_id: str) -> list[dict[str, Any]]:
        """Get all revisions recorded for a work item."""
        revs = self.execution_adapter.get_task_revisions(work_item_id)
        return [r.to_dict() for r in revs]

    def check_revision_eligibility(self, work_item_id: str) -> tuple[bool, str]:
        """Check whether work item meets criteria for autonomous revision."""
        return self.execution_adapter.check_revision_eligibility(work_item_id)
