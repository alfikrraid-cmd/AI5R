from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class ExperienceRecord:
    action: str
    result: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()


class CognitiveFeedbackLoop:

    def __init__(self):
        self.experiences = []


    def record(
        self,
        action: str,
        result: dict[str, Any]
    ):

        experience = ExperienceRecord(
            action=action,
            result=result
        )

        self.experiences.append(experience)

        return {
            "status": "RECORDED",
            "experience_count": len(self.experiences)
        }


    def learn(self):

        return {
            "status": "LEARNING",
            "samples": len(self.experiences)
        }
