from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from RUNTIME.enterprise_task import EnterpriseTask


@dataclass
class EnterpriseWorker:
    worker_type: str
    name: str
    capabilities: List[str]

    status: str = "idle"
    priority: int = 5
    department: str = "runtime"

    worker_id: str = field(default_factory=lambda: f"worker-{uuid4()}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports(self, task_type: str) -> bool:
        return task_type in self.capabilities

    def execute(self, task: EnterpriseTask) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.name} does not implement execute()"
        )

    def to_enterprise_object(self):
        return {
            "object_type": "enterprise_worker",
            "object_id": self.worker_id,
            "worker_type": self.worker_type,
            "name": self.name,
            "department": self.department,
            "status": self.status,
            "priority": self.priority,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
