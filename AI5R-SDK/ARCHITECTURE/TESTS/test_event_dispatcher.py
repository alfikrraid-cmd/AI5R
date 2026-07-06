import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import (
    EventDispatcher,
    ServiceBus,
)


def test_dispatch_event_to_handler():
    bus = ServiceBus()
    dispatcher = EventDispatcher(bus)

    received = []

    dispatcher.register_handler(
        "PROCESS_STARTED",
        lambda event: received.append(event.payload["process_id"]),
    )

    result = dispatcher.dispatch(
        event_type="PROCESS_STARTED",
        payload={"process_id": "PRC-001"},
    )

    assert received == ["PRC-001"]
    assert result.status == "DISPATCHED"
    assert result.event_type == "PROCESS_STARTED"
    assert result.handler_count == 1


def test_dispatch_without_handler():
    bus = ServiceBus()
    dispatcher = EventDispatcher(bus)

    result = dispatcher.dispatch(
        event_type="NO_HANDLER",
        payload={"ok": True},
    )

    assert result.status == "DISPATCHED"
    assert result.handler_count == 0
    assert len(bus.history()) == 1


def test_dispatch_log():
    bus = ServiceBus()
    dispatcher = EventDispatcher(bus)

    dispatcher.dispatch("A")
    dispatcher.dispatch("B")

    log = dispatcher.dispatch_log()

    assert len(log) == 2
    assert log[0].event_type == "A"
    assert log[1].event_type == "B"
    assert dispatcher.last_dispatch().event_type == "B"


def test_dispatch_metadata():
    bus = ServiceBus()
    dispatcher = EventDispatcher(bus)

    result = dispatcher.dispatch(
        event_type="WORKFLOW_READY",
        metadata={
            "source": "workflow_scheduler",
        },
    )

    assert result.metadata["source"] == "workflow_scheduler"
