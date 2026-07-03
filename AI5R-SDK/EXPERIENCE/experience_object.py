from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class ExperienceObject:
    id: str
    code: str

    warehouse_object_id: str

    observer_worker_id: str
    observer_type: str

    experience_type: str
    observation: str
    evidence: Dict[str, Any]
    confidence: float

    status: str = "active"
    version: str = "1.0.0"

    organization_id: Optional[str] = None
    thread_id: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
    policy_ids: List[str] = field(default_factory=list)

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    def is_valid(self) -> bool:
        return bool(
            self.id
            and self.code
            and self.warehouse_object_id
            and self.observer_worker_id
            and self.observer_type
            and self.experience_type
            and self.observation
            and isinstance(self.evidence, dict)
            and 0.0 <= self.confidence <= 1.0
        )
