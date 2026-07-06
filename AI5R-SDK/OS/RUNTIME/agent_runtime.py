from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AgentRuntimeState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    STOPPED = "STOPPED"


@dataclass
class AgentRuntime:
    agent_id: str

    state: AgentRuntimeState = AgentRuntimeState.IDLE

    inbox_size: int = 0
    processed_messages: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)

    started_at: str | None = None
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def start(self):
        self.state = AgentRuntimeState.RUNNING
        self.started_at = datetime.now(UTC).isoformat()
        self.updated_at = self.started_at

    def stop(self):
        self.state = AgentRuntimeState.STOPPED
        self.updated_at = datetime.now(UTC).isoformat()

    def receive(self):
        self.inbox_size += 1
        self.updated_at = datetime.now(UTC).isoformat()

    def consume(self):
        if self.inbox_size == 0:
            return

        self.inbox_size -= 1
        self.processed_messages += 1
        self.updated_at = datetime.now(UTC).isoformat()

    def snapshot(self):
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "inbox_size": self.inbox_size,
            "processed_messages": self.processed_messages,
            "metadata": dict(self.metadata),
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }
