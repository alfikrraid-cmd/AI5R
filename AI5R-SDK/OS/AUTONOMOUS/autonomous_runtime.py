from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class RuntimeStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass
class AutonomousRuntime:
    runtime_id: str

    status: RuntimeStatus = RuntimeStatus.CREATED

    cycle: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def start(self):
        self.status = RuntimeStatus.RUNNING
        self.updated_at = datetime.now(UTC).isoformat()

    def pause(self):
        self.status = RuntimeStatus.PAUSED
        self.updated_at = datetime.now(UTC).isoformat()

    def stop(self):
        self.status = RuntimeStatus.STOPPED
        self.updated_at = datetime.now(UTC).isoformat()

    def tick(self):
        if self.status != RuntimeStatus.RUNNING:
            raise RuntimeError("Runtime is not running")

        self.cycle += 1
        self.updated_at = datetime.now(UTC).isoformat()

    def snapshot(self):
        return {
            "runtime_id": self.runtime_id,
            "status": self.status.value,
            "cycle": self.cycle,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
