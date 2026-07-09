from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Sprint:
    objective: str
    organization_id: str
    department_id: str
    status: str = "CREATED"
    assigned_employee_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    manufacturing_order_ids: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    object_type: str = "SPRINT_ASSET"
    sprint_id: str = field(default_factory=lambda: f"SPRINT-{uuid4()}")

    def add_task(self, task_id: str) -> None:
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def assign_employee(self, employee_id: str) -> None:
        if employee_id not in self.assigned_employee_ids:
            self.assigned_employee_ids.append(employee_id)

    def add_manufacturing_order(self, manufacturing_order_id: str) -> None:
        if manufacturing_order_id not in self.manufacturing_order_ids:
            self.manufacturing_order_ids.append(manufacturing_order_id)

    def add_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)
