import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from OSA.EVENT_BUS_INTEGRATION import (
    OSAEventBusIntegration,
    OSAEventType,
)


def test_event_bus_integration_publishes_event():
    event_bus = OSAEventBusIntegration()

    event = event_bus.publish(
        event_type=OSAEventType.PIPELINE_STARTED,
        source="RuntimePipeline",
        payload={"goal_id": "GOAL-001"},
    )

    assert event.event_id == "OSA-EVT-000001"
    assert event.event_type == OSAEventType.PIPELINE_STARTED
    assert event.source == "RuntimePipeline"
    assert event.payload["goal_id"] == "GOAL-001"


def test_event_bus_integration_lists_events():
    event_bus = OSAEventBusIntegration()

    event_bus.publish(
        event_type=OSAEventType.PIPELINE_STARTED,
        source="RuntimePipeline",
    )

    event_bus.publish(
        event_type=OSAEventType.PIPELINE_COMPLETED,
        source="RuntimePipeline",
    )

    assert len(event_bus.list_events()) == 2


def test_event_bus_integration_filters_by_type():
    event_bus = OSAEventBusIntegration()

    event_bus.publish(
        event_type=OSAEventType.PIPELINE_STARTED,
        source="RuntimePipeline",
    )

    event_bus.publish(
        event_type=OSAEventType.MEMORY_LEARNED,
        source="MemoryLearningEngine",
    )

    memory_events = event_bus.list_by_type(OSAEventType.MEMORY_LEARNED)

    assert len(memory_events) == 1
    assert memory_events[0].source == "MemoryLearningEngine"


def test_event_bus_integration_can_clear_events():
    event_bus = OSAEventBusIntegration()

    event_bus.publish(
        event_type=OSAEventType.PIPELINE_STARTED,
        source="RuntimePipeline",
    )

    event_bus.clear()

    assert event_bus.list_events() == []
