from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    capability: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "capability": self.capability,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> SkillDefinition:
        if not skill.skill_id:
            raise ValueError("skill_id is required")

        if not skill.capability:
            raise ValueError("capability is required")

        self.skills[skill.skill_id] = skill
        return skill

    def get(self, skill_id: str) -> SkillDefinition:
        if skill_id not in self.skills:
            raise KeyError(f"Skill not found: {skill_id}")

        return self.skills[skill_id]

    def list_skills(self) -> list[SkillDefinition]:
        return list(self.skills.values())

    def find_by_capability(self, capability: str) -> list[SkillDefinition]:
        return [
            skill
            for skill in self.skills.values()
            if skill.capability == capability
        ]

    def resolve_best_skill(self, capability: str) -> SkillDefinition:
        matches = self.find_by_capability(capability)

        if not matches:
            raise KeyError(f"No skill registered for capability: {capability}")

        return matches[0]
