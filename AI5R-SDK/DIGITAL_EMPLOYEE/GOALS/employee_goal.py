from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class GoalStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class EmployeeGoal:
    employee_id: str
    title: str
    description: str = ""

    goal_id: str = field(
        default_factory=lambda: f"GOAL-{uuid4().hex[:12].upper()}"
    )

    status: GoalStatus = GoalStatus.CREATED
    progress: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("Employee ID is required")

        if not self.title:
            raise ValueError("Goal title is required")

    def update_progress(self, progress: float) -> "EmployeeGoal":
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")

        self.progress = progress

        if progress == 100:
            self.status = GoalStatus.COMPLETED
        elif progress > 0:
            self.status = GoalStatus.ACTIVE

        self.updated_at = datetime.now(UTC).isoformat()
        return self

    def snapshot(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "employee_id": self.employee_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
