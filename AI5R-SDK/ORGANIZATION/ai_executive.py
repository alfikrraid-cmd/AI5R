"""
AO-006
AI Executive Base Contract

Immutable, deterministic definition of an AI executive within the
organization. Lifecycle methods define the contract shape only; they
carry no behavior and must be implemented by concrete executives.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center and the OrganizationRuntime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class AIExecutive:
    executive_id: str
    executive_name: str
    department: str
    authority_level: str
    managed_roles: tuple[str, ...] = field(default_factory=tuple)
    policies: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.executive_id, str)
            or not self.executive_id.strip()
        ):
            raise ValueError("executive_id is required")

        if (
            not isinstance(self.executive_name, str)
            or not self.executive_name.strip()
        ):
            raise ValueError("executive_name is required")

        if not isinstance(self.department, str) or not self.department.strip():
            raise ValueError("department is required")

        if (
            not isinstance(self.authority_level, str)
            or not self.authority_level.strip()
        ):
            raise ValueError("authority_level is required")

        object.__setattr__(self, "managed_roles", tuple(self.managed_roles))
        object.__setattr__(self, "policies", tuple(self.policies))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def receive_work(self) -> None:
        raise NotImplementedError

    def plan(self) -> None:
        raise NotImplementedError

    def assign(self) -> None:
        raise NotImplementedError

    def monitor(self) -> None:
        raise NotImplementedError

    def report(self) -> None:
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {
            "executive_id": self.executive_id,
            "executive_name": self.executive_name,
            "department": self.department,
            "authority_level": self.authority_level,
            "managed_roles": list(self.managed_roles),
            "policies": list(self.policies),
            "metadata": dict(self.metadata),
        }
