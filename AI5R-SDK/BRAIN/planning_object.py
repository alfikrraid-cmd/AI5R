from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List


@dataclass
class PlanningObject:
    plan_id: str
    decision_id: str

    actions: List[Dict[str, Any]]

    priority: str = "normal"

    estimated_steps: int = 0

    status: str = "planned"

    digital_thread_id: str = ""

    enterprise_context: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):

        return {

            "plan_id": self.plan_id,
            "decision_id": self.decision_id,
            "actions": self.actions,
            "priority": self.priority,
            "estimated_steps": self.estimated_steps,
            "status": self.status,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
