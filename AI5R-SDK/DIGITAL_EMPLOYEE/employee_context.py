from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EmployeeContext:
    employee_id: str
    role: str
    department: str
    organization: str
    goals: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str | None = None

    def add_goal(self, goal: str):
        if goal not in self.goals:
            self.goals.append(goal)
            self.touch()
        return self

    def add_task(self, task: str):
        if task not in self.tasks:
            self.tasks.append(task)
            self.touch()
        return self

    def remember(
        self,
        key: str,
        value: Any,
    ):
        self.memory[key] = value
        self.touch()
        return self

    def recall(
        self,
        key: str,
        default: Any = None,
    ):
        return self.memory.get(key, default)

    def update_metadata(
        self,
        key: str,
        value: Any,
    ):
        self.metadata[key] = value
        self.touch()
        return self

    def touch(self):
        self.updated_at = datetime.now(UTC).isoformat()

    def snapshot(self):
        return {
            "employee_id": self.employee_id,
            "role": self.role,
            "department": self.department,
            "organization": self.organization,
            "goals": list(self.goals),
            "tasks": list(self.tasks),
            "memory": dict(self.memory),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
