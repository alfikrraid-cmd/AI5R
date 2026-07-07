import pytest

from OSA.GOAL_ENGINE.goal_decomposer import GoalDecomposer


def test_goal_decomposer_creates_goal_object():
    decomposer = GoalDecomposer()

    goal = decomposer.decompose("Create marketing strategy for UMKM batik")

    assert goal.goal == "Create marketing strategy for UMKM batik"
    assert goal.priority == "MEDIUM"
    assert goal.estimated_complexity == "MEDIUM"
    assert goal.goal_id.startswith("GOAL-")
    assert len(goal.subtasks) >= 5


def test_goal_decomposer_rejects_empty_goal():
    decomposer = GoalDecomposer()

    with pytest.raises(ValueError):
        decomposer.decompose("")
