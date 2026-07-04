from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class CompetencyObject:
    """
    Enterprise Competency Object

    Represents measured capability performance.
    """

    organization_id: str
    capability_id: str
    competency_code: str
    competency_name: str

    success_rate: float = 0.0
    accuracy_score: float = 0.0
    failure_rate: float = 0.0
    evidence_count: int = 0

    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    evidence_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    object_type: str = "COMPETENCY"
    competency_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "ACTIVE"

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return self.__dict__
