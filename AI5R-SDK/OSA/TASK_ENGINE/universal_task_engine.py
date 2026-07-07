from __future__ import annotations

from OSA.EVENTS.brain_event import BrainEvent
from OSA.EVENTS.brain_event_bus import BrainEventBus
from OSA.GOAL_ENGINE.goal_decomposer import GoalDecomposer

from .task_object import TaskObject
from .task_status import TaskStatus


class UniversalTaskEngine:
    def __init__(self):
        self.event_bus = BrainEventBus()
        self.goal_decomposer = GoalDecomposer()

    def submit(self, goal: str, employee_id: str = "EMP-001") -> TaskObject:
        goal_object = self.goal_decomposer.decompose(goal)

        task = TaskObject(
            goal=goal_object.goal,
            employee_id=employee_id,
            goal_id=goal_object.goal_id,
            subtasks=goal_object.subtasks,
        )

        task.status = TaskStatus.PLANNING

        self.event_bus.publish(
            BrainEvent(
                employee_id=employee_id,
                module="TASK_ENGINE",
                event="TASK_CREATED",
                status="SUCCESS",
                message=goal,
                payload={
                    "task_id": task.task_id,
                    "goal_id": task.goal_id,
                    "subtasks": task.subtasks,
                },
            )
        )

        task.status = TaskStatus.READY

        return task
