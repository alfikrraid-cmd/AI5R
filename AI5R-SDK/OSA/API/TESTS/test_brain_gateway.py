from OSA.API.brain_gateway import (
    brain_event_bus,
    get_latest_brain_events,
    publish_demo_brain_events,
)


def test_publish_demo_brain_events():
    brain_event_bus.events.clear()

    events = publish_demo_brain_events(employee_id="EMP-001")

    assert len(events) == 5
    assert events[0]["event"] == "OBSERVATION_CREATED"
    assert events[-1]["event"] == "EXECUTION_COMPLETED"


def test_get_latest_brain_events():
    brain_event_bus.events.clear()

    publish_demo_brain_events(employee_id="EMP-002")

    latest = get_latest_brain_events(limit=2)

    assert len(latest) == 2
    assert latest[0]["event"] == "EXECUTION_STARTED"
    assert latest[1]["event"] == "EXECUTION_COMPLETED"
