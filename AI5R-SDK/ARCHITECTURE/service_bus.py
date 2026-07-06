from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable


@dataclass(frozen=True)
class ServiceEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class ServiceBus:
    """
    Internal event bus for AI5R OS.
    """

    def __init__(self):
        self._handlers: dict[
            str,
            list[Callable[[ServiceEvent], None]]
        ] = defaultdict(list)

        self._history: list[ServiceEvent] = []

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[ServiceEvent], None],
    ) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: ServiceEvent) -> None:
        self._history.append(event)

        for handler in self._handlers.get(event.event_type, []):
            handler(event)

    def history(self) -> list[ServiceEvent]:
        return list(self._history)

    def subscribers(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))
