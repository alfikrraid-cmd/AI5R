"""
AO-002
Role Assignment

Immutable, deterministic assignment of an AI role to a work order.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleAssignment:
    assignment_id: str
    role_id: str
    work_order_id: str
    priority: str
    status: str
    assigned_at: Any | None = None
    deadline: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.assignment_id, str)
            or not self.assignment_id.strip()
        ):
            raise ValueError("assignment_id is required")

        if not isinstance(self.role_id, str) or not self.role_id.strip():
            raise ValueError("role_id is required")

        if (
            not isinstance(self.work_order_id, str)
            or not self.work_order_id.strip()
        ):
            raise ValueError("work_order_id is required")

        if not isinstance(self.priority, str) or not self.priority.strip():
            raise ValueError("priority is required")

        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status is required")

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "role_id": self.role_id,
            "work_order_id": self.work_order_id,
            "priority": self.priority,
            "status": self.status,
            "assigned_at": self.assigned_at,
            "deadline": self.deadline,
            "metadata": dict(self.metadata),
        }
