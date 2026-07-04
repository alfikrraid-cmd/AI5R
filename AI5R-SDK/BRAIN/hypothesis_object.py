from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List


@dataclass
class HypothesisObject:
    hypothesis_id: str
    understanding_id: str
    hypotheses: List[Dict[str, Any]]
    selected: bool = False
    status: str = "hypothesized"
    digital_thread_id: str = ""
    enterprise_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "understanding_id": self.understanding_id,
            "hypotheses": self.hypotheses,
            "selected": self.selected,
            "status": self.status,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
