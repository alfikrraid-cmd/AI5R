import pytest

from OSA.PLANNER.planner_engine import PlannerEngine
from OSA.TASK_ENGINE.task_object import TaskObject


def test_planner_creates_plan_from_task_subtasks():
    task = TaskObject(
        goal="Create marketing strategy",
        subtasks=[
            "Analyze market",
            "Define target customer",
            "Create content plan",
        ],
    )

    plan = PlannerEngine().create_plan(task)

    assert plan.plan_id.startswith("PLAN-")
    assert plan.task_id == task.task_id
    assert plan.goal == task.goal
    assert plan.steps == task.subtasks
    assert plan.status == "READY"


def test_planner_rejects_empty_goal():
    task = TaskObject(goal="")

    with pytest.raises(ValueError):
        PlannerEngine().create_plan(task)
