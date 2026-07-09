from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from WORKFORCE.digital_employee import DigitalEmployee
from WORKFORCE.digital_workforce_scheduler import DigitalWorkforceScheduler
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class MissionResult:
    mission_id: str
    status: str
    work_item_id: str
    employee_id: str
    runtime_phases: list[str]
    activity_count: int
    execution_plan: dict[str, Any]
    completed_at: str = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


class MissionOrchestrator:
    def __init__(self, activity_registry: EmployeeActivityRegistry | None = None) -> None:
        self.activity_registry = activity_registry or EmployeeActivityRegistry()
        self.employee_runtime = EmployeeRuntime(activity_registry=self.activity_registry)
        self.scheduler = DigitalWorkforceScheduler()

    def run(
        self,
        employee: DigitalEmployee,
        work_item: WorkItem,
        mission_id: str | None = None,
    ) -> MissionResult:
        resolved_mission_id = mission_id or f"MISSION-{uuid4()}"

        plan = WorkforceExecutionPlan(
            mission_id=resolved_mission_id,
            metadata={
                "objective": work_item.title,
            },
        )
        plan.add_work_item(work_item.work_item_id)

        decision = self.scheduler.next_work_item(plan)

        if decision.status != "WORK_SELECTED":
            raise ValueError("No work item available for mission execution")

        before_count = len(self.activity_registry.snapshot())
        runtime_results = self.employee_runtime.run(employee, work_item)
        self.scheduler.complete_work_item(plan, work_item.work_item_id)
        after_count = len(self.activity_registry.snapshot())

        return MissionResult(
            mission_id=resolved_mission_id,
            status="COMPLETED",
            work_item_id=work_item.work_item_id,
            employee_id=employee.employee_id,
            runtime_phases=[result.phase for result in runtime_results],
            activity_count=after_count - before_count,
            execution_plan=plan.snapshot(),
            metadata={
                "work_item_title": work_item.title,
                "employee_name": employee.employee_name,
                "position_id": employee.position_id,
            },
        )
