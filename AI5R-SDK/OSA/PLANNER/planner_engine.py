from __future__ import annotations

from OSA.TASK_ENGINE.task_object import TaskObject

from .plan_object import PlanObject


class PlannerEngine:
    def create_plan(self, task: TaskObject) -> PlanObject:
        if not task.goal or not task.goal.strip():
            raise ValueError("Task goal is required")

        steps = task.subtasks if task.subtasks else [
            "Understand task objective",
            "Define execution steps",
            "Execute task",
            "Evaluate result",
        ]

        return PlanObject(
            task_id=task.task_id,
            goal=task.goal,
            steps=steps,
            status="READY",
        )
