from dataclasses import dataclass, field
from typing import Any

from .registry import WorkforceRegistry
from .worker import Worker


@dataclass
class WorkOrder:
    work_order_id: str
    objective: str
    required_role: str | None = None
    required_skills: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkAssignment:
    work_order_id: str
    worker_id: str
    worker_role: str
    objective: str
    status: str = "ASSIGNED"


class WorkAssignmentEngine:
    def __init__(self, registry: WorkforceRegistry) -> None:
        self.registry = registry

    def assign(self, work_order: WorkOrder) -> WorkAssignment:
        candidates = self.registry.find_available(
            required_role=work_order.required_role,
            required_skills=work_order.required_skills,
        )

        if not candidates:
            raise ValueError("No available worker can handle this work order")

        worker: Worker = candidates[0]
        worker.assign()

        return WorkAssignment(
            work_order_id=work_order.work_order_id,
            worker_id=worker.worker_id,
            worker_role=worker.role,
            objective=work_order.objective,
        )

    def complete(
        self,
        assignment: WorkAssignment,
        experience_object: dict[str, Any] | None = None,
    ) -> WorkAssignment:
        worker = self.registry.get(assignment.worker_id)

        if experience_object:
            worker.add_experience(experience_object)

        worker.release()
        assignment.status = "COMPLETED"
        return assignment
