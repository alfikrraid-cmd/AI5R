from typing import List

from EXPERIENCE.experience_object import ExperienceObject


class ExperienceValidationEngine:
    def validate(self, obj: ExperienceObject) -> bool:
        return obj.is_valid()

    def validate_batch(self, objects: List[ExperienceObject]) -> bool:
        return all(self.validate(obj) for obj in objects)

    def errors(self, obj: ExperienceObject) -> List[str]:
        errors = []

        if not obj.id:
            errors.append("Missing id")
        if not obj.code:
            errors.append("Missing code")
        if not obj.warehouse_object_id:
            errors.append("Missing warehouse_object_id")
        if not obj.observer_worker_id:
            errors.append("Missing observer_worker_id")
        if not obj.observer_type:
            errors.append("Missing observer_type")
        if not obj.experience_type:
            errors.append("Missing experience_type")
        if not obj.observation:
            errors.append("Missing observation")
        if not isinstance(obj.evidence, dict):
            errors.append("Evidence must be dict")
        if not isinstance(obj.confidence, float):
            errors.append("Confidence must be float")
        elif not 0.0 <= obj.confidence <= 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")

        return errors
