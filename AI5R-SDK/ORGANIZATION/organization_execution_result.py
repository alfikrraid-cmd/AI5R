"""
AO-005
Organization Execution Result

Immutable, deterministic aggregate outcome of an OrganizationRuntime
execution across multiple role assignments.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center, OrganizationRuntime,
AIRole, and RoleAssignment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationExecutionResult:
    status: str
    completed_roles: tuple[str, ...] = field(default_factory=tuple)
    failed_roles: tuple[str, ...] = field(default_factory=tuple)
    execution_order: tuple[str, ...] = field(default_factory=tuple)
    results: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status is required")

        object.__setattr__(self, "completed_roles", tuple(self.completed_roles))
        object.__setattr__(self, "failed_roles", tuple(self.failed_roles))
        object.__setattr__(self, "execution_order", tuple(self.execution_order))
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "completed_roles": list(self.completed_roles),
            "failed_roles": list(self.failed_roles),
            "execution_order": list(self.execution_order),
            "results": list(self.results),
            "metadata": dict(self.metadata),
        }
