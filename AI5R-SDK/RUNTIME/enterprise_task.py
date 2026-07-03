from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4


@dataclass
class EnterpriseTask:
    task_type: str
    title: str
    instruction: str
    mission_id: str
    status: str = "created"
    priority: int = 5
    assigned_worker: str | None = None
    task_id: str = field(default_factory=lambda: f"task-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input_object: Dict[str, Any] = field(default_factory=dict)
    output_object: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_enterprise_object(self) -> Dict[str, Any]:
        return {
            "object_type": "enterprise_task",
            "object_id": self.task_id,
            "task_type": self.task_type,
            "title": self.title,
            "instruction": self.instruction,
            "mission_id": self.mission_id,
            "status": self.status,
            "priority": self.priority,
            "assigned_worker": self.assigned_worker,
            "created_at": self.created_at,
            "input_object": self.input_object,
            "output_object": self.output_object,
            "metadata": self.metadata,
        }

    def assign(self, worker_id: str) -> None:
        self.assigned_worker = worker_id
        self.status = "assigned"

    def start(self) -> None:
        if self.status not in ["created", "assigned"]:
            raise ValueError("Task can only start from created or assigned status")
        self.status = "running"

    def complete(self, output_object: Dict[str, Any]) -> None:
        self.output_object = output_object
        self.status = "completed"

    def fail(self, reason: str) -> None:
        self.status = "failed"
        self.metadata["failure_reason"] = reason
