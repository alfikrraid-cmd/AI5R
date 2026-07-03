from typing import Any, List

from EXPERIENCE.experience_object import ExperienceObject
from EXPERIENCE.experience_registry import ExperienceRegistry


class ExperienceQueryEngine:
    def __init__(self, registry: ExperienceRegistry):
        self.registry = registry

    def all(self) -> List[ExperienceObject]:
        return self.registry.list_all()

    def by_warehouse_object(self, warehouse_object_id: str) -> List[ExperienceObject]:
        return self.registry.find_by_warehouse_object(warehouse_object_id)

    def by_observer(self, observer_worker_id: str) -> List[ExperienceObject]:
        return self.registry.find_by_observer(observer_worker_id)

    def by_experience_type(self, experience_type: str) -> List[ExperienceObject]:
        return self.registry.find_by_experience_type(experience_type)

    def by_policy(self, policy_id: str) -> List[ExperienceObject]:
        return [
            obj for obj in self.registry.list_all()
            if policy_id in obj.policy_ids
        ]

    def by_metadata(self, key: str, value: Any) -> List[ExperienceObject]:
        return [
            obj for obj in self.registry.list_all()
            if obj.metadata.get(key) == value
        ]

    def by_min_confidence(self, min_confidence: float) -> List[ExperienceObject]:
        return [
            obj for obj in self.registry.list_all()
            if obj.confidence >= min_confidence
        ]
