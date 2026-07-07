from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class BusinessDecision:

    decision_type: str
    recommendation: str
    priority: str
    created_at: str = datetime.now(UTC).isoformat()



class UMKMDecisionEngine:


    def __init__(self):

        self.decisions = []



    def analyze(
        self,
        business_data: dict[str, Any]
    ):


        if business_data.get(
            "sales_decline"
        ):


            decision = BusinessDecision(

                decision_type="GROWTH_RECOVERY",

                recommendation=
                "Create customer retention campaign",

                priority="HIGH"

            )


        else:


            decision = BusinessDecision(

                decision_type="GROWTH",

                recommendation=
                "Optimize current marketing strategy",

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
