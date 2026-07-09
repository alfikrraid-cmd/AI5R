from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Mission:
    title: str
    description: str = ""
    requester: str = "Human Owner"
    priority: str = "MEDIUM"
    status: str = "INTAKE"
    leader: str = "Raid"
    participants: list[str] = field(default_factory=list)
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    mission_id: str = field(default_factory=lambda: f"MISSION-{uuid4()}")
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def update_status(self, status: str) -> None:
        self.status = status
        self.updated_at = _now()

    def assign_executive_review(
        self,
        leader: str,
        participants: list[str],
    ) -> None:
        self.leader = leader
        self.participants = participants
        self.update_status("EXECUTIVE_REVIEW")

    def approve(self, recommendation: str) -> None:
        self.recommendation = recommendation
        self.update_status("APPROVED")

    def start_manufacturing(self) -> None:
        self.update_status("MANUFACTURING")

    def deliver(self) -> None:
        self.update_status("DELIVERED")

    def snapshot(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "description": self.description,
            "requester": self.requester,
            "priority": self.priority,
            "status": self.status,
            "leader": self.leader,
            "participants": self.participants,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
