from OSA.EVENTS.brain_event import BrainEvent
from OSA.EVENTS.brain_event_bus import BrainEventBus


def test_brain_event_bus_publish_and_list():
    bus = BrainEventBus()

    event = BrainEvent(
        employee_id="EMP-001",
        module="MEMORY",
        event="MEMORY_STORED",
        status="SUCCESS",
        message="Memory stored.",
    )

    published = bus.publish(event)

    assert published == event
    assert len(bus.list_events()) == 1
    assert bus.list_events()[0]["event"] == "MEMORY_STORED"


def test_brain_event_bus_subscriber_receives_event():
    bus = BrainEventBus()
    received = []

    def subscriber(event):
        received.append(event)

    bus.subscribe(subscriber)

    event = BrainEvent(
        employee_id="EMP-001",
        module="EXECUTION",
        event="EXECUTION_STARTED",
        status="RUNNING",
        message="Execution started.",
    )

    bus.publish(event)

    assert received[0] == event
