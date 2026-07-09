from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


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
