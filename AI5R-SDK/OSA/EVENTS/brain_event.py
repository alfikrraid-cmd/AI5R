from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class BrainEvent:
    employee_id: str
    module: str
    event: str
    status: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"BE-{uuid4().hex[:12].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "employee_id": self.employee_id,
            "module": self.module,
            "event": self.event,
            "status": self.status,
            "message": self.message,
            "payload": self.payload,
        }
