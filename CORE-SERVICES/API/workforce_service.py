from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parent
CORE_SERVICES_DIR = API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for _path in (API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

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
from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.it_department_operating_model import ITDepartmentOperatingModel
from WORKFORCE.it_department_pack import ITDepartmentPack
from WORKFORCE.organization import Organization
from WORKFORCE.work_board import WorkBoard
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_event_bus import WorkforceEvent, WorkforceEventBus

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
    "LTSA_REPORT_ANALYST": "LTSA Report Analyst",
}


class WorkforceService:
    """Canonical service managing AI5R Digital Workforce runtime and read models."""

    def __init__(
        self,
        organization_name: str = "AI5R Enterprise",
        live_stream_api: LiveStreamAPI | None = None,
    ) -> None:
        self.organization = Organization(organization_name=organization_name)
        manufactured = ITDepartmentPack().manufacture(self.organization)
        self.department = manufactured["department"]
        self.employees: list[DigitalEmployee] = manufactured["employees"]

        # Canonical NEXA operational report analyst employee
        self._nexa_employee = DigitalEmployee(
            employee_name="NEXA",
            organization_id=self.organization.organization_id,
            identity_id="ID-LTSA_REPORT_ANALYST",
            position_id="LTSA_REPORT_ANALYST",
            kernel_id="KERNEL-AI5R",
            capability_ids=["LTSA_OPERATIONAL_REPORT_DRAFT"],
            status="ACTIVE",
            employee_id="NEXA_LTSA_REPORT_ANALYST",
            metadata={
                "role": "LTSA Report Analyst",
                "department_id": self.department.department_id,
                "department_name": self.department.department_name,
            },
        )

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

    def find_employee(self, employee_id_or_pos: str) -> DigitalEmployee | None:
        norm = employee_id_or_pos.upper().strip()
        if norm in ("NEXA_LTSA_REPORT_ANALYST", "LTSA_REPORT_ANALYST", "NEXA"):
            return self._nexa_employee
        if employee_id_or_pos in self._employee_by_id:
            return self._employee_by_id[employee_id_or_pos]
        if employee_id_or_pos in self._employee_by_pos:
            return self._employee_by_pos[employee_id_or_pos]
        # Match case-insensitively
        if norm in self._employee_by_pos:
            return self._employee_by_pos[norm]
        for e in self.employees:
            if e.employee_id.upper() == norm or e.employee_name.upper() == norm:
                return e
        return None

    def start_pilot(self, *, actor, repository, executor, mission_type, input_text, idempotency_key):
        from time import perf_counter
        from API.workforce_text_executor import REQUESTED_POLICY

        executor.validate(mission_type, input_text)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
            raise ValueError("Invalid idempotency key")
        employee = self.find_employee_by_position("DOCUMENTATION_ENGINEER")
        if employee is None:
            raise ValueError("Documentation employee unavailable")
        run, created = repository.claim(
            organization_id=actor.organization_id, requester_id=actor.user_id,
            idempotency_key=idempotency_key, mission_type=mission_type,
            requested_policy=REQUESTED_POLICY,
            employee={"employee_id": employee.employee_id, "identity_id": employee.identity_id,
                      "position_id": employee.position_id, "employee_name": employee.employee_name},
        )
        if not created:
            return run
        started = perf_counter()
        try:
            result = executor.execute(mission_type, input_text)
        except Exception:
            # Never store exception strings: providers may include credentials or prompts.
            result = None
        return repository.finish_execution(
            run["run_id"], result=result, elapsed_ms=round((perf_counter() - started) * 1000),
        )

    def start_nexa_mission(
        self,
        *,
        actor,
        repository,
        executor,
        mission_type,
        start_date,
        end_date,
        area=None,
        idempotency_key,
    ):
        from time import perf_counter
        from API.workforce_nexa_executor import REQUESTED_POLICY

        executor.validate(mission_type, start_date, end_date, area)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
            raise ValueError("Invalid idempotency key")
        employee = self.find_employee("NEXA_LTSA_REPORT_ANALYST")
        if employee is None:
            raise ValueError("NEXA employee unavailable")
        run, created = repository.claim(
            organization_id=actor.organization_id,
            requester_id=actor.user_id,
            idempotency_key=idempotency_key,
            mission_type=mission_type,
            requested_policy=REQUESTED_POLICY,
            employee={
                "employee_id": employee.employee_id,
                "identity_id": employee.identity_id,
                "position_id": employee.position_id,
                "employee_name": employee.employee_name,
            },
        )
        if not created:
            return run
        started = perf_counter()
        try:
            result = executor.execute(
                mission_type=mission_type,
                start_date=start_date,
                end_date=end_date,
                area=area,
                mission_id=run["run_id"],
            )
        except Exception:
            # Never store raw exception strings: providers may leak credentials or sensitive tokens.
            result = None
        return repository.finish_execution(
            run["run_id"],
            result=result,
            elapsed_ms=round((perf_counter() - started) * 1000),
            evidence=getattr(result, "evidence", None),
        )

    def get_pilot(self, *, actor, repository, run_id):
        run = repository.get(run_id)
        if run["organization_id"] != actor.organization_id:
            raise KeyError("Pilot run not found")
        return run

    def review_pilot(self, *, actor, repository, run_id, decision, draft_version, note):
        self.get_pilot(actor=actor, repository=repository, run_id=run_id)
        # Completion approves text only; no release/event/tool/action dispatch.
        return repository.review(run_id, reviewer_id=actor.user_id, decision=decision,
                                 draft_version=draft_version, note=note)

    def find_employee_by_position(self, position_id: str) -> DigitalEmployee | None:
        return self._employee_by_pos.get(position_id) or self._employee_by_pos.get(position_id.upper())

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
            "metadata": dict(item.metadata),
            "is_production": is_production_work_item(item),
        }

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
        return self.operating_model.release(work_item_id, approval=approval)

