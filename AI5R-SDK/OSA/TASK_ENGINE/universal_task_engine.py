from __future__ import annotations

from OSA.EVENTS.brain_event import BrainEvent
from OSA.EVENTS.brain_event_bus import BrainEventBus

from .task_object import TaskObject
from .task_status import TaskStatus


class UniversalTaskEngine:
    def __init__(self):
        self.event_bus = BrainEventBus()

    def submit(self, goal: str, employee_id: str = "EMP-001") -> TaskObject:
        task = TaskObject(
            goal=goal,
            employee_id=employee_id,
        )

        task.status = TaskStatus.PLANNING

        self.event_bus.publish(
            BrainEvent(
                employee_id=employee_id,
                module="TASK_ENGINE",
                event="TASK_CREATED",
                status="SUCCESS",
                message=goal,
                payload={"task_id": task.task_id},
            )
        )

        task.status = TaskStatus.READY

        return task
