from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List


@dataclass
class OutcomeObject:
    outcome_id: str
    execution_id: str

    completed_tasks: List[Dict[str, Any]]

    success: bool

    completion_rate: float

    status: str = "completed"

    digital_thread_id: str = ""

    enterprise_context: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):

        return {
            "outcome_id": self.outcome_id,
            "execution_id": self.execution_id,
            "completed_tasks": self.completed_tasks,
            "success": self.success,
            "completion_rate": self.completion_rate,
            "status": self.status,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
