from collections import defaultdict
from datetime import datetime, UTC


class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._history = []

    def subscribe(self, event_name: str, handler):
        if not callable(handler):
            raise ValueError("handler must be callable")

        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload=None):
        event = {
            "event_name": event_name,
            "payload": payload or {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self._history.append(event)

        for handler in self._subscribers[event_name]:
            handler(event)

        return event

    def subscribers(self, event_name: str):
        return list(self._subscribers[event_name])

    def history(self):
        return list(self._history)
