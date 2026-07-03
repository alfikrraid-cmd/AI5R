from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class EnterpriseMission:
    mission_type: str
    title: str
    objective: str
    source_object_id: str | None = None
    customer_id: str | None = None
    status: str = "created"
    mission_id: str = field(default_factory=lambda: f"mission-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_enterprise_object(self) -> Dict[str, Any]:
        return {
            "object_type": "enterprise_mission",
            "object_id": self.mission_id,
            "mission_type": self.mission_type,
            "title": self.title,
            "objective": self.objective,
            "source_object_id": self.source_object_id,
            "customer_id": self.customer_id,
            "status": self.status,
            "created_at": self.created_at,
            "tasks": self.tasks,
            "metadata": self.metadata,
        }

    def add_task(self, task: Dict[str, Any]) -> None:
        self.tasks.append(task)

    def start(self) -> None:
        if self.status != "created":
            raise ValueError("Mission can only start from created status")
        self.status = "running"

    def complete(self) -> None:
        self.status = "completed"

    def fail(self, reason: str) -> None:
        self.status = "failed"
        self.metadata["failure_reason"] = reason
