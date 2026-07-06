from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class EvidenceObject:

    evidence_name: str

    source_type: str

    source_ids: list[str]

    sample_size: int

    success_count: int

    failure_count: int

    confidence_score: float

    measurement_period: str

    metrics: dict[str, Any] = field(default_factory=dict)

    supporting_artifacts: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    object_type: str = "EVIDENCE"

    status: str = "COLLECTED"

    evidence_id: str = field(
        default_factory=lambda: f"EVD-{uuid4()}"
    )
