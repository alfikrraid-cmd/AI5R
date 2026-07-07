from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .brain_event import BrainEvent


class BrainEventBus:
    def __init__(self):
        self.events: list[BrainEvent] = []
        self.subscribers: list[Callable[[BrainEvent], Any]] = []

    def publish(self, event: BrainEvent) -> BrainEvent:
        self.events.append(event)

        for subscriber in self.subscribers:
            subscriber(event)

        return event

    def subscribe(self, subscriber: Callable[[BrainEvent], Any]) -> None:
        self.subscribers.append(subscriber)

    def list_events(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events[-limit:]]
