from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry


def test_employee_activity_can_be_recorded():
    registry = EmployeeActivityRegistry()

    activity = EmployeeActivity(
        employee_id="EMP-001",
        activity_type="THINKING",
        status="IN_PROGRESS",
        message="Selecting capability",
        progress=25,
        work_item_id="WORK-001",
    )

    registry.record(activity)

    assert registry.list_all() == [activity]
    assert registry.latest_by_employee("EMP-001") == activity


def test_employee_activity_can_be_updated():
    activity = EmployeeActivity(
        employee_id="EMP-001",
        activity_type="THINKING",
        status="IN_PROGRESS",
        message="Thinking",
        progress=10,
    )

    activity.update(
        status="COMPLETED",
        message="Capability selected",
        progress=100,
        metadata={"selected_capability": "API"},
    )

    assert activity.status == "COMPLETED"
    assert activity.message == "Capability selected"
    assert activity.progress == 100
    assert activity.metadata["selected_capability"] == "API"


def test_employee_activity_rejects_invalid_progress():
    activity = EmployeeActivity(
        employee_id="EMP-001",
        activity_type="THINKING",
        status="IN_PROGRESS",
        message="Thinking",
    )

    try:
        activity.update(
            status="IN_PROGRESS",
            message="Invalid",
            progress=101,
        )
    except ValueError as exc:
        assert "progress must be between 0 and 100" in str(exc)
    else:
        raise AssertionError("Expected invalid progress to fail")


def test_registry_snapshot_for_dashboard():
    registry = EmployeeActivityRegistry()

    activity = EmployeeActivity(
        employee_id="EMP-001",
        activity_type="CLAIMED_WORK",
        status="CLAIMED",
        message="Backend claimed work item",
        progress=15,
        work_item_id="WORK-001",
        sprint_id="SPRINT-001",
    )

    registry.record(activity)

    snapshot = registry.snapshot()

    assert snapshot[0]["employee_id"] == "EMP-001"
    assert snapshot[0]["status"] == "CLAIMED"
    assert snapshot[0]["progress"] == 15
    assert snapshot[0]["work_item_id"] == "WORK-001"
