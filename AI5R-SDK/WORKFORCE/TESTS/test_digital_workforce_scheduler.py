from WORKFORCE.digital_workforce_scheduler import DigitalWorkforceScheduler
from WORKFORCE.workforce_execution_plan import WorkforceExecutionPlan


def test_scheduler_selects_ready_work_item():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")
    plan.add_work_item("WORK-BACKEND")
    plan.add_work_item("WORK-QA", dependencies=["WORK-BACKEND"])

    decision = DigitalWorkforceScheduler().next_work_item(plan)

    assert decision.status == "WORK_SELECTED"
    assert decision.work_item_id == "WORK-BACKEND"
    assert plan.running == ["WORK-BACKEND"]
    assert plan.blocked == ["WORK-QA"]


def test_scheduler_returns_no_ready_work_when_all_blocked():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")
    plan.add_work_item("WORK-QA", dependencies=["WORK-BACKEND"])

    decision = DigitalWorkforceScheduler().next_work_item(plan)

    assert decision.status == "NO_READY_WORK"
    assert decision.work_item_id is None
    assert plan.blocked == ["WORK-QA"]


def test_scheduler_completion_unblocks_dependent_work():
    plan = WorkforceExecutionPlan(mission_id="MISSION-001")
    plan.add_work_item("WORK-BACKEND")
    plan.add_work_item("WORK-QA", dependencies=["WORK-BACKEND"])

    scheduler = DigitalWorkforceScheduler()

    first = scheduler.next_work_item(plan)
    scheduler.complete_work_item(plan, first.work_item_id)

    assert plan.completed == ["WORK-BACKEND"]
    assert plan.waiting == ["WORK-QA"]
    assert plan.blocked == []

    second = scheduler.next_work_item(plan)

    assert second.status == "WORK_SELECTED"
    assert second.work_item_id == "WORK-QA"
    assert plan.running == ["WORK-QA"]


def test_scheduler_decision_is_dashboard_ready():
    plan = WorkforceExecutionPlan(
        mission_id="MISSION-001",
        metadata={"objective": "Build Login API"},
    )
    plan.add_work_item("WORK-BACKEND")

    decision = DigitalWorkforceScheduler().next_work_item(plan)

    assert decision.metadata["mission_id"] == "MISSION-001"
    assert decision.metadata["metadata"]["objective"] == "Build Login API"
    assert decision.metadata["running"] == ["WORK-BACKEND"]
