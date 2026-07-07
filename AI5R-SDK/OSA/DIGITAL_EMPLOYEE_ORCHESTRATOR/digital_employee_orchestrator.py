from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EmployeeAssignmentStatus(str, Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class DigitalEmployeeAssignment:
    assignment_id: str
    task_id: str
    employee_id: str
    capability_id: str
    status: EmployeeAssignmentStatus = EmployeeAssignmentStatus.CREATED
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class DigitalEmployeeOrchestrator:
    def __init__(self):
        self.assignments: dict[str, DigitalEmployeeAssignment] = {}

    def assign(
        self,
        task: dict[str, Any],
        capability_assignment: dict[str, Any],
    ) -> DigitalEmployeeAssignment:
        task_id = task.get("task_id")
        employee_id = capability_assignment.get("employee_id")
        capability_id = capability_assignment.get("capability_id")

        if not task_id:
            raise ValueError("task_id is required")

        if not employee_id:
            raise ValueError("employee_id is required")

        if not capability_id:
            raise ValueError("capability_id is required")

        assignment_id = f"DEA-{task_id}-{employee_id}"

        assignment = DigitalEmployeeAssignment(
            assignment_id=assignment_id,
            task_id=task_id,
            employee_id=employee_id,
            capability_id=capability_id,
            status=EmployeeAssignmentStatus.ASSIGNED,
            payload={
                "task": task,
                "capability_assignment": capability_assignment,
            },
        )

        self.assignments[assignment_id] = assignment
        return assignment

    def dispatch(self, assignment_id: str) -> DigitalEmployeeAssignment:
        assignment = self._get_assignment(assignment_id)
        assignment.status = EmployeeAssignmentStatus.DISPATCHED
        assignment.updated_at = datetime.now(UTC).isoformat()
        return assignment

    def complete(self, assignment_id: str) -> DigitalEmployeeAssignment:
        assignment = self._get_assignment(assignment_id)
        assignment.status = EmployeeAssignmentStatus.COMPLETED
        assignment.updated_at = datetime.now(UTC).isoformat()
        return assignment

    def fail(self, assignment_id: str) -> DigitalEmployeeAssignment:
        assignment = self._get_assignment(assignment_id)
        assignment.status = EmployeeAssignmentStatus.FAILED
        assignment.updated_at = datetime.now(UTC).isoformat()
        return assignment

    def _get_assignment(self, assignment_id: str) -> DigitalEmployeeAssignment:
        if assignment_id not in self.assignments:
            raise KeyError(f"Assignment not found: {assignment_id}")
        return self.assignments[assignment_id]
