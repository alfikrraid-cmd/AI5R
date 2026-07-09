from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Organization:
    organization_name: str
    status: str = "ACTIVE"
    department_ids: list[str] = field(default_factory=list)
    employee_ids: list[str] = field(default_factory=list)
    sprint_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    object_type: str = "ORGANIZATION"
    organization_id: str = field(default_factory=lambda: f"ORG-{uuid4()}")

    def add_department(self, department_id: str) -> None:
        if department_id not in self.department_ids:
            self.department_ids.append(department_id)

    def add_employee(self, employee_id: str) -> None:
        if employee_id not in self.employee_ids:
            self.employee_ids.append(employee_id)

    def add_sprint(self, sprint_id: str) -> None:
        if sprint_id not in self.sprint_ids:
            self.sprint_ids.append(sprint_id)
