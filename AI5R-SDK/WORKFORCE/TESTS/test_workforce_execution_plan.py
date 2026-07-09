from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


def test_execution_plan_tracks_waiting_and_blocked_items():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")

    plan.add_work_item("WORK-BACKEND")
    plan.add_work_item("WORK-QA", dependencies=["WORK-BACKEND"])

    assert plan.ready_items() == ["WORK-BACKEND"]
    assert plan.waiting == ["WORK-BACKEND"]
    assert plan.blocked == ["WORK-QA"]
    assert plan.dependency_graph["WORK-QA"] == ["WORK-BACKEND"]


def test_execution_plan_moves_item_to_running():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")
    plan.add_work_item("WORK-BACKEND")

    plan.mark_running("WORK-BACKEND")

    assert plan.running == ["WORK-BACKEND"]
    assert plan.waiting == []


def test_execution_plan_unblocks_dependencies_after_completion():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")

    plan.add_work_item("WORK-BACKEND")
    plan.add_work_item("WORK-QA", dependencies=["WORK-BACKEND"])

    plan.mark_running("WORK-BACKEND")
    plan.mark_completed("WORK-BACKEND")

    assert plan.completed == ["WORK-BACKEND"]
    assert plan.blocked == []
    assert plan.waiting == ["WORK-QA"]
    assert plan.ready_items() == ["WORK-QA"]


def test_execution_plan_snapshot_is_dashboard_ready():
    plan = WorkforceExecutionPlan(
        mission_id="MISSION-001",
        metadata={"objective": "Build Login API"},
    )

    plan.add_work_item("WORK-BACKEND")

    snapshot = plan.snapshot()

    assert snapshot["plan_id"].startswith("WEP-")
    assert snapshot["mission_id"] == "MISSION-001"
    assert snapshot["metadata"]["objective"] == "Build Login API"
    assert snapshot["waiting"] == ["WORK-BACKEND"]
