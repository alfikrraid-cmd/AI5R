from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class EmployeeSkill:
    employee_id: str
    skill_name: str

    skill_id: str = field(
        default_factory=lambda: f"SKILL-{uuid4().hex[:12].upper()}"
    )

    level: int = 1
    experience_points: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        if not self.employee_id:
            raise ValueError("Employee ID is required")

        if not self.skill_name:
            raise ValueError("Skill name is required")

        if self.level < 1:
            raise ValueError("Skill level must be at least 1")

    def add_experience(self, points: int) -> "EmployeeSkill":
        if points <= 0:
            raise ValueError("Experience points must be positive")

        self.experience_points += points

        while self.experience_points >= self.level * 100:
            self.experience_points -= self.level * 100
            self.level += 1

        self.updated_at = datetime.now(UTC).isoformat()
        return self

    def snapshot(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "employee_id": self.employee_id,
            "skill_name": self.skill_name,
            "level": self.level,
            "experience_points": self.experience_points,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
