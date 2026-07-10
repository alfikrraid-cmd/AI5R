"""
AO-001
AI Role Contract

Immutable, deterministic definition of an AI role within the
organization.

This component holds no behavior beyond validation and conversion. It
is independent of the Manufacturing Center.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class AIRole:
    role_id: str
    role_name: str
    department: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    responsibilities: tuple[str, ...] = field(default_factory=tuple)
    input_contracts: tuple[str, ...] = field(default_factory=tuple)
    output_contracts: tuple[str, ...] = field(default_factory=tuple)
    policies: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.role_id, str) or not self.role_id.strip():
            raise ValueError("role_id is required")

        if not isinstance(self.role_name, str) or not self.role_name.strip():
            raise ValueError("role_name is required")

        if not isinstance(self.department, str) or not self.department.strip():
            raise ValueError("department is required")

        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(
            self, "responsibilities", tuple(self.responsibilities)
        )
        object.__setattr__(
            self, "input_contracts", tuple(self.input_contracts)
        )
        object.__setattr__(
            self, "output_contracts", tuple(self.output_contracts)
        )
        object.__setattr__(self, "policies", tuple(self.policies))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "department": self.department,
            "capabilities": list(self.capabilities),
            "responsibilities": list(self.responsibilities),
            "input_contracts": list(self.input_contracts),
            "output_contracts": list(self.output_contracts),
            "policies": list(self.policies),
            "metadata": dict(self.metadata),
        }
