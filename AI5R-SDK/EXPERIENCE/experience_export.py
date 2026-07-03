from typing import Any, Dict, List

from EXPERIENCE.experience_object import ExperienceObject


class ExperienceExportContract:
    def export_object(self, obj: ExperienceObject) -> Dict[str, Any]:
        return {
            "experience_id": obj.id,
            "code": obj.code,
            "warehouse_object_id": obj.warehouse_object_id,
            "observer": {
                "worker_id": obj.observer_worker_id,
                "type": obj.observer_type,
            },
            "experience_type": obj.experience_type,
            "observation": obj.observation,
            "evidence": obj.evidence,
            "confidence": obj.confidence,
            "context": {
                "organization_id": obj.organization_id,
                "thread_id": obj.thread_id,
                "policy_ids": obj.policy_ids,
            },
            "metadata": obj.metadata,
            "version": obj.version,
            "status": obj.status,
            "timestamps": {
                "created_at": obj.created_at,
                "updated_at": obj.updated_at,
            },
        }

    def export_batch(self, objects: List[ExperienceObject]) -> List[Dict[str, Any]]:
        return [self.export_object(obj) for obj in objects]
