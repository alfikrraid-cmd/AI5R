from typing import Any, Dict, List, Optional

from EXPERIENCE.experience_object import ExperienceObject
from EXPERIENCE.experience_registry import ExperienceRegistry
from EXPERIENCE.experience_collector import ExperienceCollectorEngine
from EXPERIENCE.experience_validation import ExperienceValidationEngine


class ExperiencePipeline:
    def __init__(self):
        self.registry = ExperienceRegistry()
        self.collector = ExperienceCollectorEngine(self.registry)
        self.validator = ExperienceValidationEngine()

    def process(
        self,
        warehouse_object_id: str,
        observer_worker_id: str,
        observer_type: str,
        experience_type: str,
        observation: str,
        evidence: Dict[str, Any],
        confidence: float,
        organization_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        policy_ids: Optional[List[str]] = None,
    ) -> ExperienceObject:
        obj = self.collector.collect(
            warehouse_object_id=warehouse_object_id,
            observer_worker_id=observer_worker_id,
            observer_type=observer_type,
            experience_type=experience_type,
            observation=observation,
            evidence=evidence,
            confidence=confidence,
            organization_id=organization_id,
            thread_id=thread_id,
            metadata=metadata,
            policy_ids=policy_ids,
        )

        if not self.validator.validate(obj):
            raise ValueError(self.validator.errors(obj))

        return obj

    def list_all(self) -> List[ExperienceObject]:
        return self.registry.list_all()
