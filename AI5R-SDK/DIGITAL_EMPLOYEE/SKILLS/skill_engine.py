from __future__ import annotations

from .employee_skill import EmployeeSkill


class SkillEngine:
    def __init__(self):
        self._skills: dict[str, EmployeeSkill] = {}
        self._employee_index: dict[str, list[str]] = {}

    def register_skill(
        self,
        employee_id: str,
        skill_name: str,
    ) -> EmployeeSkill:

        skill = EmployeeSkill(
            employee_id=employee_id,
            skill_name=skill_name,
        )

        self._skills[skill.skill_id] = skill
        self._employee_index.setdefault(employee_id, []).append(skill.skill_id)

        return skill

    def get_skill(self, skill_id: str):
        return self._skills.get(skill_id)

    def require_skill(self, skill_id: str):
        skill = self.get_skill(skill_id)

        if skill is None:
            raise KeyError(f"Skill not found: {skill_id}")

        return skill

    def gain_experience(
        self,
        skill_id: str,
        points: int,
    ):
        return self.require_skill(skill_id).add_experience(points)

    def list_skills(
        self,
        employee_id: str,
    ):
        return [
            self._skills[sid]
            for sid in self._employee_index.get(employee_id, [])
        ]

    def snapshot(self):
        return {
            sid: skill.snapshot()
            for sid, skill in self._skills.items()
        }
