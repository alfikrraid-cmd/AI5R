from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict


@dataclass
class DecisionObject:
    decision_id: str
    hypothesis_id: str
    selected_hypothesis: Dict[str, Any]
    rationale: str
    confidence: float
    status: str = "decided"
    digital_thread_id: str = ""
    enterprise_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self):
        return {
            "decision_id": self.decision_id,
            "hypothesis_id": self.hypothesis_id,
            "selected_hypothesis": self.selected_hypothesis,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "status": self.status,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
