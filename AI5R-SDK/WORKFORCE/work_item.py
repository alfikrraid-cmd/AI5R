from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class WorkItem:
    title: str
    assigned_position_id: str
    description: str = ""
    status: str = "CREATED"
    assigned_employee_id: str | None = None
    manufacturing_order_id: str | None = None
    artifact_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    work_item_id: str = field(default_factory=lambda: f"WORK-{uuid4()}")

    @property
    def task_id(self) -> str:
        return self.work_item_id
