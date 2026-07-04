from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict


@dataclass
class UnderstandingObject:
    understanding_id: str
    observation_id: str
    meaning: str
    confidence: float
    digital_thread_id: str
    enterprise_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "understanding_id": self.understanding_id,
            "observation_id": self.observation_id,
            "meaning": self.meaning,
            "confidence": self.confidence,
            "digital_thread_id": self.digital_thread_id,
            "enterprise_context": self.enterprise_context,
            "created_at": self.created_at,
        }
