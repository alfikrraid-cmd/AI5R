"""One server-owned synthetic text mission. No tools, memory or action runtime."""
from dataclasses import dataclass

from API.engineering_ai_client import EngineeringAIClient

MISSION_TYPE = "WORKFORCE_TEXT_DOCUMENTATION_PILOT"
REQUESTED_POLICY = "DAHONO_PRIMARY"
SYNTHETIC_TEXT = (
    "Fictional paper boat exercise: fold a blank sheet, name the boat Example, "
    "and place it on an empty desk. Write a short documentation draft describing these steps."
)


@dataclass(frozen=True)
class DraftExecutionResult:
    content: str
    actual_provider: str
    actual_model: str
    finish_reason: str
    fallback_used: bool
    outcome: str
    requested_policy: str = REQUESTED_POLICY


class WorkforceTextExecutor:
    def __init__(self, client: EngineeringAIClient):
        self.client = client

    @staticmethod
    def validate(mission_type: str, input_text: str) -> None:
        # An attestation or keyword denylist cannot establish non-sensitivity.
        # R1 accepts exactly this public server-owned fixture, not arbitrary text.
        if mission_type != MISSION_TYPE or input_text != SYNTHETIC_TEXT:
            raise ValueError("Only the server-owned synthetic documentation fixture is allowed")

    def execute(self, mission_type: str, input_text: str) -> DraftExecutionResult:
        self.validate(mission_type, input_text)
        response = self.client.generate_response(
            input_text,
            system_prompt="Produce only a short plain text DRAFT for the fictional exercise. Do not perform actions or request tools.",
            metadata={"mission_type": MISSION_TYPE},
        )
        if (not isinstance(response.content, str) or not response.content.strip()
                or len(response.content) > 16000 or not response.provider or not response.model):
            raise ValueError("Invalid bounded draft response")
        fallback = response.provider != "DAHONO"
        return DraftExecutionResult(
            content=response.content, actual_provider=response.provider,
            actual_model=response.model, finish_reason=response.finish_reason,
            fallback_used=fallback,
            outcome="FALLBACK_SUCCESS" if fallback else "DAHONO_SUCCESS",
        )
