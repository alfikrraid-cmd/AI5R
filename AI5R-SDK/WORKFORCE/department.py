from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from WORKFORCE.sprint_factory import SprintFactory


@dataclass
class Department:
    department_name: str
    organization_id: str
    status: str = "ACTIVE"
    employee_ids: list[str] = field(default_factory=list)
    sprint_ids: list[str] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    object_type: str = "DEPARTMENT"
    department_id: str = field(default_factory=lambda: f"DEPT-{uuid4()}")

    def add_employee(self, employee_id: str) -> None:
        if employee_id not in self.employee_ids:
            self.employee_ids.append(employee_id)

    def add_sprint(self, sprint_id: str) -> None:
        if sprint_id not in self.sprint_ids:
            self.sprint_ids.append(sprint_id)

    def add_capability(self, capability_id: str) -> None:
        if capability_id not in self.capability_ids:
            self.capability_ids.append(capability_id)

    def start_sprint(self, objective: str, metadata: dict[str, Any] | None = None):
        result = SprintFactory().manufacture(
            objective=objective,
            organization_id=self.organization_id,
            department_id=self.department_id,
            metadata=metadata or {},
        )

        sprint = result["asset"]
        self.add_sprint(sprint.sprint_id)

        return {
            "status": "SPRINT_STARTED",
            "department_id": self.department_id,
            "sprint": sprint,
        }
