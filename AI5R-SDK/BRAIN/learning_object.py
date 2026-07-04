from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Any


@dataclass
class LearningObject:

    learning_id: str

    outcome_id: str

    lesson: str

    confidence_delta: float

    knowledge_update_required: bool

    status: str = "learned"

    digital_thread_id: str = ""

    enterprise_context: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self):

        return {

            "learning_id": self.learning_id,

            "outcome_id": self.outcome_id,

            "lesson": self.lesson,

            "confidence_delta": self.confidence_delta,

            "knowledge_update_required": self.knowledge_update_required,

            "status": self.status,

            "digital_thread_id": self.digital_thread_id,

            "enterprise_context": self.enterprise_context,

            "created_at": self.created_at,
        }
