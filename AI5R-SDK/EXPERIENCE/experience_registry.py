from typing import Dict, List, Optional

from EXPERIENCE.experience_object import ExperienceObject


class ExperienceRegistry:
    def __init__(self):
        self.objects: Dict[str, ExperienceObject] = {}

    def register(self, obj: ExperienceObject) -> ExperienceObject:
        if not obj.is_valid():
            raise ValueError("Invalid ExperienceObject")

        self.objects[obj.id] = obj
        return obj

    def get(self, object_id: str) -> Optional[ExperienceObject]:
        return self.objects.get(object_id)

    def list_all(self) -> List[ExperienceObject]:
        return list(self.objects.values())

    def find_by_warehouse_object(self, warehouse_object_id: str) -> List[ExperienceObject]:
        return [
            obj for obj in self.objects.values()
            if obj.warehouse_object_id == warehouse_object_id
        ]

    def find_by_observer(self, observer_worker_id: str) -> List[ExperienceObject]:
        return [
            obj for obj in self.objects.values()
            if obj.observer_worker_id == observer_worker_id
        ]

    def find_by_experience_type(self, experience_type: str) -> List[ExperienceObject]:
        return [
            obj for obj in self.objects.values()
            if obj.experience_type == experience_type
        ]
