"""
AO-007
Executive Work Order

Immutable, deterministic directive issued to an AI executive.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center, the OrganizationRuntime,
and AIExecutive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutiveWorkOrder:
    work_order_id: str
    mission_id: str | None = None
    objective: str
    priority: str
    constraints: tuple[str, ...] = field(default_factory=tuple)
    success_criteria: tuple[str, ...] = field(default_factory=tuple)
    requested_roles: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.work_order_id, str)
            or not self.work_order_id.strip()
        ):
            raise ValueError("work_order_id is required")

        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ValueError("objective is required")

        if not isinstance(self.priority, str) or not self.priority.strip():
            raise ValueError("priority is required")

        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(
            self, "success_criteria", tuple(self.success_criteria)
        )
        object.__setattr__(
            self, "requested_roles", tuple(self.requested_roles)
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "mission_id": self.mission_id,
            "objective": self.objective,
            "priority": self.priority,
            "constraints": list(self.constraints),
            "success_criteria": list(self.success_criteria),
            "requested_roles": list(self.requested_roles),
            "metadata": dict(self.metadata),
        }
