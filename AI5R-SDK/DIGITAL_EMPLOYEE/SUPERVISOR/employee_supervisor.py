from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class SupervisorDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    ESCALATED = "ESCALATED"


@dataclass
class EmployeeSupervisorReview:
    employee_id: str
    supervisor_id: str
    decision: SupervisorDecision | str

    review_id: str = field(
        default_factory=lambda: f"REV-{uuid4().hex[:12].upper()}"
    )

    comments: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    reviewed_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("Employee ID is required")

        if not self.supervisor_id:
            raise ValueError("Supervisor ID is required")

        if isinstance(self.decision, str):
            self.decision = SupervisorDecision(self.decision)

    def snapshot(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "employee_id": self.employee_id,
            "supervisor_id": self.supervisor_id,
            "decision": self.decision.value,
            "comments": self.comments,
            "metadata": dict(self.metadata),
            "reviewed_at": self.reviewed_at,
        }
