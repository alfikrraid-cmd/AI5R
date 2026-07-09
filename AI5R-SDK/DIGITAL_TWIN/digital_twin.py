from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DigitalTwin:
    entity_id: str
    entity_type: str
    status: str = "ACTIVE"
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    twin_id: str = field(default_factory=lambda: f"TWIN-{uuid4()}")
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def update_state(self, updates: dict[str, Any]) -> None:
        self.state.update(updates)
        self.updated_at = _now()

    def set_status(self, status: str) -> None:
        self.status = status
        self.updated_at = _now()

    def snapshot(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "status": self.status,
            "state": self.state,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
