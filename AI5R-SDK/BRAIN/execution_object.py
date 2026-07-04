from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List


@dataclass
class ExecutionObject:
    execution_id: str
    plan_id: str

    tasks: List[Dict[str, Any]]

    status: str = "ready"

    progress: float = 0.0

    digital_thread_id: str = ""

    enterprise_context: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):

        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "tasks": self.tasks,
            "status": self.status,
            "progress": self.progress,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
