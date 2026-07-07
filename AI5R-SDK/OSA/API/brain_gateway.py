from __future__ import annotations

from OSA.EVENTS.brain_event import BrainEvent
from OSA.EVENTS.brain_event_bus import BrainEventBus


brain_event_bus = BrainEventBus()


def publish_demo_brain_events(employee_id: str = "EMP-001") -> list[dict]:
    events = [
        BrainEvent(
            employee_id=employee_id,
            module="OBSERVATION",
            event="OBSERVATION_CREATED",
            status="SUCCESS",
            message="Observation created from command input.",
        ),
        BrainEvent(
            employee_id=employee_id,
            module="MEMORY",
            event="MEMORY_STORED",
            status="SUCCESS",
            message="Memory stored from observation.",
        ),
        BrainEvent(
            employee_id=employee_id,
            module="REASONING",
            event="PLAN_GENERATED",
            status="SUCCESS",
            message="Reasoning plan generated.",
        ),
        BrainEvent(
            employee_id=employee_id,
            module="EXECUTION",
            event="EXECUTION_STARTED",
            status="RUNNING",
            message="Execution started.",
        ),
        BrainEvent(
            employee_id=employee_id,
            module="EXECUTION",
            event="EXECUTION_COMPLETED",
            status="SUCCESS",
            message="Execution completed.",
        ),
    ]

    return [brain_event_bus.publish(event).to_dict() for event in events]


def get_latest_brain_events(limit: int = 20) -> list[dict]:
    return brain_event_bus.latest(limit=limit)
