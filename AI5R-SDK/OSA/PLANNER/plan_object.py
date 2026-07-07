from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class PlanObject:
    task_id: str
    goal: str
    steps: list[str]
    plan_id: str = field(default_factory=lambda: f"PLAN-{uuid4().hex[:10].upper()}")
    status: str = "CREATED"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "goal": self.goal,
            "steps": self.steps,
            "status": self.status,
            "created_at": self.created_at,
        }
