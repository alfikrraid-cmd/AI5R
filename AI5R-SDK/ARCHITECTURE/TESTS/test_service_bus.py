import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import (
    ServiceBus,
    ServiceEvent,
)


def test_publish_event():
    bus = ServiceBus()

    received = []

    bus.subscribe(
        "BOOT",
        lambda event: received.append(event.payload["status"]),
    )

    bus.publish(
        ServiceEvent(
            event_type="BOOT",
            payload={"status": "READY"},
        )
    )

    assert received == ["READY"]


def test_event_history():
    bus = ServiceBus()

    bus.publish(ServiceEvent("A"))
    bus.publish(ServiceEvent("B"))

    history = bus.history()

    assert len(history) == 2
    assert history[0].event_type == "A"
    assert history[1].event_type == "B"


def test_multiple_subscribers():
    bus = ServiceBus()

    count = []

    bus.subscribe("BOOT", lambda e: count.append(1))
    bus.subscribe("BOOT", lambda e: count.append(2))

    bus.publish(ServiceEvent("BOOT"))

    assert len(count) == 2
    assert bus.subscribers("BOOT") == 2


def test_unknown_event():
    bus = ServiceBus()

    bus.publish(ServiceEvent("UNKNOWN"))

    assert len(bus.history()) == 1
