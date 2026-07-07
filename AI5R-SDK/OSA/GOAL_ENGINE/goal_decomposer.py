from __future__ import annotations

from .goal_object import GoalObject


class GoalDecomposer:
    def decompose(self, goal: str) -> GoalObject:
        if not goal or not goal.strip():
            raise ValueError("Goal is required")

        subtasks = [
            "Understand the goal context",
            "Identify required capabilities",
            "Create execution plan",
            "Assign work to digital employee",
            "Execute planned tasks",
            "Evaluate result",
            "Store learning into memory",
        ]

        return GoalObject(
            goal=goal,
            priority="MEDIUM",
            estimated_complexity="MEDIUM",
            subtasks=subtasks,
        )
