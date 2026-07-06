from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .employee_state import EmployeeState


@dataclass
class EmployeeRuntimeEngine:
    employee_id: str
    employee_name: str

    state: EmployeeState = EmployeeState.CREATED

    current_goal: str | None = None
    current_task: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    history: list[str] = field(default_factory=list)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def start(self):
        self.state = EmployeeState.READY
        self.history.append("START")
        return self.state

    def observe(self):
        self.state = EmployeeState.OBSERVING
        self.history.append("OBSERVE")
        return self.state

    def think(self):
        self.state = EmployeeState.PLANNING
        self.history.append("THINK")
        return self.state

    def decide(self):
        self.state = EmployeeState.PLANNING
        self.history.append("DECIDE")
        return self.state

    def execute(self):
        self.state = EmployeeState.WORKING
        self.history.append("EXECUTE")
        return self.state

    def learn(self):
        self.state = EmployeeState.LEARNING
        self.history.append("LEARN")
        return self.state

    def wait(self):
        self.state = EmployeeState.READY
        self.history.append("WAIT")
        return self.state

    def stop(self):
        self.state = EmployeeState.SUSPENDED
        self.history.append("STOP")
        return self.state

    def assign_goal(self, goal: str):
        self.current_goal = goal

    def assign_task(self, task: str):
        self.current_task = task

    def snapshot(self):
        return {
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "state": self.state.value,
            "goal": self.current_goal,
            "task": self.current_task,
            "history": list(self.history),
        }
