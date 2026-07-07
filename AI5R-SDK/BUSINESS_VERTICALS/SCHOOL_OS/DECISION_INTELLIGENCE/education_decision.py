from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class EducationDecision:

    category: str
    insight: str
    recommendation: str
    priority: str
    created_at: str = datetime.now(UTC).isoformat()



class SchoolDecisionEngine:


    def __init__(self):

        self.decisions = []



    def analyze(
        self,
        data: dict[str, Any]
    ):


        if data.get(
            "learning_decline"
        ):


            decision = EducationDecision(

                category="LEARNING_RECOVERY",

                insight=
                "Student learning performance decreased",

                recommendation=
                "Create remediation program and monitor progress",

                priority="HIGH"

            )


        else:


            decision = EducationDecision(

                category="LEARNING_OPTIMIZATION",

                insight=
                "Learning performance stable",

                recommendation=
                "Continue current learning strategy",

                priority="MEDIUM"

            )



        self.decisions.append(
            decision
        )


        return {

            "status":"GENERATED",

            "priority":
            decision.priority,

            "recommendation":
            decision.recommendation

        }
