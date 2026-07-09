from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class MemoryObject:
    mission_id: str
    mission_title: str
    executive: str
    decision: str
    outcome: str
    lessons_learned: list[str] = field(default_factory=list)
    confidence: int = 80
    metadata: dict[str, Any] = field(default_factory=dict)
    memory_id: str = field(default_factory=lambda: f"MEM-{uuid4()}")
    created_at: str = field(default_factory=_now)

    def snapshot(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "mission_id": self.mission_id,
            "mission_title": self.mission_title,
            "executive": self.executive,
            "decision": self.decision,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
