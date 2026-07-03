from typing import Any, Dict, List, Optional
from uuid import uuid4

from EXPERIENCE.experience_object import ExperienceObject
from EXPERIENCE.experience_registry import ExperienceRegistry


class ExperienceCollectorEngine:
    def __init__(self, registry: ExperienceRegistry):
        self.registry = registry

    def collect(
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
        obj = ExperienceObject(
            id=str(uuid4()),
            code=f"EXP-{warehouse_object_id}",
            warehouse_object_id=warehouse_object_id,
            observer_worker_id=observer_worker_id,
            observer_type=observer_type,
            experience_type=experience_type,
            observation=observation,
            evidence=evidence,
            confidence=confidence,
            organization_id=organization_id,
            thread_id=thread_id,
            metadata=metadata or {},
            policy_ids=policy_ids or [],
        )

        return self.registry.register(obj)
