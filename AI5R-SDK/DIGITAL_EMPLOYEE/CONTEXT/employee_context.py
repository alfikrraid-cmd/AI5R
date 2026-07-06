from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EmployeeContext:
    employee_id: str
    role: str | None = None
    department_id: str | None = None
    organization_id: str | None = None
    active_goal: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def update(self, **kwargs: Any) -> "EmployeeContext":
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"Unknown employee context field: {key}")
            setattr(self, key, value)

        self.updated_at = datetime.now(UTC).isoformat()
        return self

    def attach_metadata(self, key: str, value: Any) -> "EmployeeContext":
        if not key:
            raise ValueError("Metadata key is required")

        self.metadata[key] = value
        self.updated_at = datetime.now(UTC).isoformat()
        return self

    def snapshot(self) -> dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "role": self.role,
            "department_id": self.department_id,
            "organization_id": self.organization_id,
            "active_goal": self.active_goal,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
