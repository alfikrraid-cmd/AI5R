import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EVENT_BUS import EventBus


def test_event_bus_publish_calls_subscribers():
    bus = EventBus()

    received = []

    def handler(event):
        received.append(event)

    bus.subscribe("PROCESS_STARTED", handler)

    event = bus.publish(
        "PROCESS_STARTED",
        {
            "process": "DIGITAL_EMPLOYEE",
        },
    )

    assert len(received) == 1
    assert received[0] == event
    assert event["event_name"] == "PROCESS_STARTED"
    assert event["payload"]["process"] == "DIGITAL_EMPLOYEE"


def test_event_bus_keeps_history():
    bus = EventBus()

    bus.publish("A")
    bus.publish("B")

    history = bus.history()

    assert len(history) == 2
    assert history[0]["event_name"] == "A"
    assert history[1]["event_name"] == "B"


def test_event_bus_lists_subscribers():
    bus = EventBus()

    def handler(event):
        pass

    bus.subscribe("TEST", handler)

    assert len(bus.subscribers("TEST")) == 1


def test_event_bus_requires_callable_handler():
    bus = EventBus()

    try:
        bus.subscribe("TEST", "invalid")
    except ValueError as error:
        assert str(error) == "handler must be callable"
    else:
        raise AssertionError("Expected ValueError")
