from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from .task_status import TaskStatus


@dataclass
class TaskObject:
    goal: str
    employee_id: str = ""
    goal_id: str = ""
    subtasks: list[str] = field(default_factory=list)
    task_id: str = field(default_factory=lambda: f"TASK-{uuid4().hex[:10].upper()}")
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
