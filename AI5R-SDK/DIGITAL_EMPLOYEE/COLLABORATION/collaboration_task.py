from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class CollaborationStatus(str, Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class CollaborationTask:
    owner_employee_id: str
    assigned_employee_id: str
    title: str
    description: str = ""

    task_id: str = field(
        default_factory=lambda: f"COL-{uuid4().hex[:12].upper()}"
    )

    status: CollaborationStatus = CollaborationStatus.CREATED
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self):
        if not self.owner_employee_id:
            raise ValueError("Owner employee ID is required")

        if not self.assigned_employee_id:
            raise ValueError("Assigned employee ID is required")

        if not self.title:
            raise ValueError("Task title is required")

    def change_status(
        self,
        status: CollaborationStatus | str,
    ) -> "CollaborationTask":

        if isinstance(status, str):
            status = CollaborationStatus(status)

        self.status = status
        self.updated_at = datetime.now(UTC).isoformat()
        return self

    def snapshot(self):
        return {
            "task_id": self.task_id,
            "owner_employee_id": self.owner_employee_id,
            "assigned_employee_id": self.assigned_employee_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
