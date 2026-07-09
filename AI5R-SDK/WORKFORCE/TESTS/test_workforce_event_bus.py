from WORKFORCE.employee_activity import EmployeeActivity
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.workforce_event_bus import WorkforceEvent, WorkforceEventBus


def test_workforce_event_bus_publishes_events():
    bus = WorkforceEventBus()

    event = WorkforceEvent(
        event_type="EMPLOYEE_ACTIVITY_RECORDED",
        source="WORKFORCE",
        payload={
            "employee_id": "EMP-001",
            "status": "THINKING",
        },
    )

    bus.publish(event)

    assert bus.all() == [event]
    assert bus.by_type("EMPLOYEE_ACTIVITY_RECORDED") == [event]
    assert bus.stream()[0]["payload"]["employee_id"] == "EMP-001"


def test_activity_registry_publishes_event_when_activity_recorded():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    activity = EmployeeActivity(
        employee_id="EMP-001",
        activity_type="THINKING",
        status="IN_PROGRESS",
        message="Selecting capability",
        progress=25,
        work_item_id="WORK-001",
    )

    registry.record(activity)

    events = bus.by_type("EMPLOYEE_ACTIVITY_RECORDED")

    assert len(events) == 1
    assert events[0].payload["employee_id"] == "EMP-001"
    assert events[0].payload["activity_type"] == "THINKING"
    assert events[0].payload["progress"] == 25


def test_activity_event_stream_is_dashboard_ready():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    registry.record(
        EmployeeActivity(
            employee_id="EMP-BACKEND-001",
            activity_type="CLAIMED_WORK",
            status="CLAIMED",
            message="Backend claimed work",
            progress=15,
            work_item_id="WORK-LOGIN-001",
            sprint_id="SPRINT-001",
        )
    )

    stream = bus.stream()

    assert stream[0]["event_type"] == "EMPLOYEE_ACTIVITY_RECORDED"
    assert stream[0]["source"] == "WORKFORCE"
    assert stream[0]["payload"]["status"] == "CLAIMED"
    assert stream[0]["payload"]["work_item_id"] == "WORK-LOGIN-001"
