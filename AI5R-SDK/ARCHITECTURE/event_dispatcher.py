from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .service_bus import ServiceBus, ServiceEvent


@dataclass(frozen=True)
class DispatchResult:
    event_type: str
    handler_count: int
    status: str = "DISPATCHED"
    metadata: dict[str, Any] = field(default_factory=dict)


class EventDispatcher:
    """
    Coordinates event dispatching through the AI5R Service Bus.
    """

    def __init__(self, service_bus: ServiceBus):
        self._service_bus = service_bus
        self._dispatch_log: list[DispatchResult] = []

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[ServiceEvent], None],
    ) -> None:
        self._service_bus.subscribe(
            event_type=event_type,
            handler=handler,
        )

    def dispatch(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DispatchResult:
        handler_count = self._service_bus.subscribers(event_type)

        self._service_bus.publish(
            ServiceEvent(
                event_type=event_type,
                payload=payload or {},
            )
        )

        result = DispatchResult(
            event_type=event_type,
            handler_count=handler_count,
            metadata=metadata or {},
        )

        self._dispatch_log.append(result)
        return result

    def dispatch_log(self) -> list[DispatchResult]:
        return list(self._dispatch_log)

    def last_dispatch(self) -> DispatchResult | None:
        if not self._dispatch_log:
            return None

        return self._dispatch_log[-1]
