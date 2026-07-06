from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Callable, Any


@dataclass
class EventMessage:
    event_type: str
    payload: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()


class EventBus:

    def __init__(self):
        self.subscribers = {}

    def subscribe(
        self,
        event_type: str,
        handler: Callable
    ):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)

    def publish(
        self,
        event: EventMessage
    ):

        handlers = self.subscribers.get(
            event.event_type,
            []
        )

        results = []

        for handler in handlers:
            results.append(
                handler(event)
            )

        return results
