from dataclasses import dataclass, field
from typing import Any


@dataclass
class Worker:
    worker_id: str
    name: str
    role: str
    department: str
    skills: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    status: str = "AVAILABLE"

    def can_handle(self, required_role: str | None = None, required_skills: list[str] | None = None) -> bool:
        if self.status != "AVAILABLE":
            return False

        if required_role and self.role != required_role:
            return False

        if required_skills:
            return all(skill in self.skills for skill in required_skills)

        return True

    def assign(self) -> None:
        if self.status != "AVAILABLE":
            raise ValueError("Worker is not available")
        self.status = "BUSY"

    def release(self) -> None:
        self.status = "AVAILABLE"

    def add_experience(self, experience_object: dict[str, Any]) -> None:
        self.experience.append(experience_object)

        learned_skills = experience_object.get("learned_skills", [])
        for skill in learned_skills:
            if skill not in self.skills:
                self.skills.append(skill)

        learned_capabilities = experience_object.get("learned_capabilities", [])
        for capability in learned_capabilities:
            if capability not in self.capabilities:
                self.capabilities.append(capability)
