from dataclasses import dataclass
from datetime import datetime, timezone

from .employee_state import EmployeeState


@dataclass
class EmployeeLifecycleEvent:
    from_state: str
    to_state: str
    reason: str
    created_at: str


class EmployeeLifecycle:
    def __init__(self, initial_state: str = EmployeeState.CREATED.value):
        self.state = initial_state
        self.events: list[EmployeeLifecycleEvent] = []

    def transition(self, to_state: str, reason: str):
        event = EmployeeLifecycleEvent(
            from_state=self.state,
            to_state=to_state,
            reason=reason,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.events.append(event)
        self.state = to_state
        return event

    def initialize(self):
        return self.transition(EmployeeState.INITIALIZED.value, "employee_initialized")

    def ready(self):
        return self.transition(EmployeeState.READY.value, "employee_ready")

    def plan(self):
        return self.transition(EmployeeState.PLANNING.value, "task_planning_started")

    def work(self):
        return self.transition(EmployeeState.WORKING.value, "task_execution_started")

    def observe(self):
        return self.transition(EmployeeState.OBSERVING.value, "task_observation_started")

    def learn(self):
        return self.transition(EmployeeState.LEARNING.value, "task_learning_started")

    def suspend(self):
        return self.transition(EmployeeState.SUSPENDED.value, "employee_suspended")
