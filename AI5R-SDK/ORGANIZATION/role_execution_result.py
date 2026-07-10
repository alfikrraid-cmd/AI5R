"""
AO-003
Role Execution Result

Immutable, deterministic outcome of a single role assignment
execution.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class RoleExecutionResult:
    execution_id: str
    assignment_id: str
    role_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.execution_id, str)
            or not self.execution_id.strip()
        ):
            raise ValueError("execution_id is required")

        if (
            not isinstance(self.assignment_id, str)
            or not self.assignment_id.strip()
        ):
            raise ValueError("assignment_id is required")

        if not isinstance(self.role_id, str) or not self.role_id.strip():
            raise ValueError("role_id is required")

        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status is required")

        object.__setattr__(self, "outputs", dict(self.outputs))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "assignment_id": self.assignment_id,
            "role_id": self.role_id,
            "status": self.status,
            "outputs": dict(self.outputs),
            "artifacts": list(self.artifacts),
            "metadata": dict(self.metadata),
        }
