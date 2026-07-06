from DIGITAL_EMPLOYEE.GOALS import GoalEngine, GoalStatus


def test_create_goal():
    engine = GoalEngine()

    goal = engine.create_goal(
        "EMP-001",
        "Increase Sales",
    )

    assert goal.status == GoalStatus.CREATED
    assert goal.progress == 0


def test_progress_update():
    engine = GoalEngine()

    goal = engine.create_goal(
        "EMP-001",
        "Increase Sales",
    )

    engine.update_progress(goal.goal_id, 50)

    assert goal.progress == 50
    assert goal.status == GoalStatus.ACTIVE


def test_complete_goal():
    engine = GoalEngine()

    goal = engine.create_goal(
        "EMP-001",
        "Increase Sales",
    )

    engine.update_progress(goal.goal_id, 100)

    assert goal.status == GoalStatus.COMPLETED


def test_list_goals():
    engine = GoalEngine()

    engine.create_goal("EMP-001", "A")
    engine.create_goal("EMP-001", "B")
    engine.create_goal("EMP-002", "C")

    assert len(engine.list_goals("EMP-001")) == 2


def test_active_goals():
    engine = GoalEngine()

    goal = engine.create_goal("EMP-001", "A")

    engine.update_progress(goal.goal_id, 100)

    engine.create_goal("EMP-001", "B")

    assert len(engine.active_goals("EMP-001")) == 1


def test_snapshot():
    engine = GoalEngine()

    goal = engine.create_goal(
        "EMP-001",
        "Planning",
    )

    snapshot = engine.snapshot()

    assert goal.goal_id in snapshot
