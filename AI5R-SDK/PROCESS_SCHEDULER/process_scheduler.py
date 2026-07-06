from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4


PRIORITY_ORDER = {
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


@dataclass
class ScheduledProcess:
    process_id: str
    process_name: str
    priority: str = "MEDIUM"
    payload: dict[str, Any] = field(default_factory=dict)
    schedule_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "QUEUED"
    requested_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProcessScheduler:
    def __init__(self):
        self._queue = []

    def schedule(self, process_id: str, process_name: str, priority: str = "MEDIUM", payload=None):
        if not process_id:
            raise ValueError("process_id is required")

        if not process_name or not process_name.strip():
            raise ValueError("process_name is required")

        priority = priority.upper()

        if priority not in PRIORITY_ORDER:
            raise ValueError("priority must be HIGH, MEDIUM, or LOW")

        scheduled = ScheduledProcess(
            process_id=process_id,
            process_name=process_name.strip().upper().replace(" ", "_").replace("-", "_"),
            priority=priority,
            payload=payload or {},
        )

        self._queue.append(scheduled)
        self._queue.sort(key=lambda item: PRIORITY_ORDER[item.priority])

        return scheduled

    def next(self):
        if not self._queue:
            return None

        scheduled = self._queue.pop(0)
        scheduled.status = "DISPATCHED"
        return scheduled

    def queue(self):
        return list(self._queue)

    def cancel(self, schedule_id: str):
        for item in self._queue:
            if item.schedule_id == schedule_id:
                self._queue.remove(item)
                item.status = "CANCELLED"
                return item

        return None
