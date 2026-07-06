from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class DecisionObject:
    context_id: str
    objective: str
    options: list[dict[str, Any]]
    selected_option: dict[str, Any]
    rationale: str
    confidence_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    object_type: str = "DECISION"
    decision_id: str = field(default_factory=lambda: f"DEC-{uuid4()}")
    status: str = "DECIDED"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
