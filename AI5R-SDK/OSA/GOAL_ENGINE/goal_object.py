from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class GoalObject:
    goal: str
    priority: str = "MEDIUM"
    estimated_complexity: str = "MEDIUM"
    subtasks: list[str] = field(default_factory=list)
    goal_id: str = field(default_factory=lambda: f"GOAL-{uuid4().hex[:10].upper()}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "goal": self.goal,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "subtasks": self.subtasks,
            "created_at": self.created_at,
        }
