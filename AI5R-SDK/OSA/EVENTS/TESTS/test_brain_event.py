from OSA.EVENTS.brain_event import BrainEvent


def test_brain_event_to_dict():
    event = BrainEvent(
        employee_id="EMP-001",
        module="REASONING",
        event="PLAN_CREATED",
        status="SUCCESS",
        message="Plan created.",
        payload={"task_id": "TASK-001"},
    )

    data = event.to_dict()

    assert data["employee_id"] == "EMP-001"
    assert data["module"] == "REASONING"
    assert data["event"] == "PLAN_CREATED"
    assert data["status"] == "SUCCESS"
    assert data["payload"]["task_id"] == "TASK-001"
    assert data["event_id"].startswith("BE-")
