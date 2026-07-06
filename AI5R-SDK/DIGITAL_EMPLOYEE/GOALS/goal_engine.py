from __future__ import annotations

from .employee_goal import EmployeeGoal


class GoalEngine:
    def __init__(self):
        self._goals: dict[str, EmployeeGoal] = {}
        self._employee_index: dict[str, list[str]] = {}

    def create_goal(
        self,
        employee_id: str,
        title: str,
        description: str = "",
    ) -> EmployeeGoal:

        goal = EmployeeGoal(
            employee_id=employee_id,
            title=title,
            description=description,
        )

        self._goals[goal.goal_id] = goal
        self._employee_index.setdefault(employee_id, []).append(goal.goal_id)

        return goal

    def get_goal(self, goal_id: str):
        return self._goals.get(goal_id)

    def require_goal(self, goal_id: str):
        goal = self.get_goal(goal_id)

        if goal is None:
            raise KeyError(f"Goal not found: {goal_id}")

        return goal

    def update_progress(
        self,
        goal_id: str,
        progress: float,
    ):
        goal = self.require_goal(goal_id)
        return goal.update_progress(progress)

    def list_goals(
        self,
        employee_id: str,
    ):
        return [
            self._goals[g]
            for g in self._employee_index.get(employee_id, [])
        ]

    def active_goals(
        self,
        employee_id: str,
    ):
        return [
            goal
            for goal in self.list_goals(employee_id)
            if goal.status.value in ("CREATED", "ACTIVE")
        ]

    def snapshot(self):
        return {
            goal_id: goal.snapshot()
            for goal_id, goal in self._goals.items()
        }
