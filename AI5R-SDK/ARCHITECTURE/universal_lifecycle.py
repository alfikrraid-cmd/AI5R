from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


_ALLOWED_TRANSITIONS = {
    "draft": {"active"},
    "active": {"paused", "completed", "failed", "deprecated"},
    "paused": {"active"},
    "completed": {"archived"},
    "failed": {"archived"},
    "deprecated": {"archived"},
    "archived": {"deleted"},
    "deleted": set(),
}


@dataclass
class LifecycleTransition:

    from_status: str
    to_status: str

    timestamp: str

    reason: str | None = None


@dataclass
class UniversalLifecycle:

    status: str = "draft"

    lifecycle_history: list[LifecycleTransition] = field(default_factory=list)

    last_transition: str | None = None

    last_transition_reason: str | None = None

    updated_at: str | None = None

    def transition(self, new_status: str, reason: str | None = None):

        allowed = _ALLOWED_TRANSITIONS.get(self.status, set())

        if new_status not in allowed:
            raise ValueError(
                f"Invalid lifecycle transition: {self.status} -> {new_status}"
            )

        now = datetime.utcnow().isoformat()

        self.lifecycle_history.append(
            LifecycleTransition(
                from_status=self.status,
                to_status=new_status,
                timestamp=now,
                reason=reason,
            )
        )

        self.last_transition = f"{self.status}->{new_status}"

        self.last_transition_reason = reason

        self.status = new_status

        self.updated_at = now

    def to_dict(self):

        return {
            "status": self.status,
            "updated_at": self.updated_at,
            "last_transition": self.last_transition,
            "last_transition_reason": self.last_transition_reason,
            "history": [
                {
                    "from": h.from_status,
                    "to": h.to_status,
                    "timestamp": h.timestamp,
                    "reason": h.reason,
                }
                for h in self.lifecycle_history
            ],
        }
