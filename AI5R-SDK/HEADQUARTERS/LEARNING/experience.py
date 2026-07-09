from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _now():
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Experience:

    mission_id: str

    executive: str

    lesson: str

    outcome: str

    confidence: int = 80

    experience_id: str = field(
        default_factory=lambda: f"EXP-{uuid4()}"
    )

    created_at: str = field(
        default_factory=_now
    )

    def snapshot(self):

        return {

            "experience_id": self.experience_id,

            "mission_id": self.mission_id,

            "executive": self.executive,

            "lesson": self.lesson,

            "outcome": self.outcome,

            "confidence": self.confidence,

            "created_at": self.created_at,

        }

