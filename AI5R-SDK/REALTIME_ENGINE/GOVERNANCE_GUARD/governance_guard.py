from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class GovernanceDecision:

    status: str
    reason: str
    created_at: str = datetime.now(UTC).isoformat()



class RealtimeGovernanceGuard:


    def __init__(self):

        self.decisions = []



    def check(
        self,
        action: dict[str, Any]
    ):

        blocked_words = [
            "illegal",
            "harm",
            "fraud"
        ]


        action_text = str(action).lower()


        for word in blocked_words:

            if word in action_text:

                decision = GovernanceDecision(
                    status="BLOCKED",
                    reason=f"contains restricted term: {word}"
                )

                self.decisions.append(decision)

                return {
                    "status": decision.status,
                    "reason": decision.reason
                }



        decision = GovernanceDecision(
            status="ALLOWED",
            reason="passed governance check"
        )


        self.decisions.append(decision)


        return {
            "status": decision.status,
            "reason": decision.reason
        }
