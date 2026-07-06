from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class RuntimeSnapshot:
    runtime_id: str
    state: dict[str, Any]

    snapshot_id: str = field(
        default_factory=lambda: f"SNAP-{uuid4().hex[:12].upper()}"
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.runtime_id:
            raise ValueError("Runtime ID is required")

        if not isinstance(self.state, dict):
            raise ValueError("State must be a dictionary")

    def snapshot(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "runtime_id": self.runtime_id,
            "state": dict(self.state),
            "created_at": self.created_at,
        }
