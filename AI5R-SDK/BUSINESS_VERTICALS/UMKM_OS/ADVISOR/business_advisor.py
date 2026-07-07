from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class AdvisorResponse:

    insight: str
    recommendation: str
    priority: str
    created_at: str = datetime.now(UTC).isoformat()



class UMKMBusinessAdvisor:


    def analyze(
        self,
        data: dict[str, Any]
    ):


        if data.get(
            "sales_decline"
        ):


            return AdvisorResponse(

                insight=
                "Business performance declining",

                recommendation=
                "Launch retention campaign and optimize product focus",

                priority="HIGH"

            )


        return AdvisorResponse(

            insight=
            "Business performance stable",

            recommendation=
            "Continue optimization strategy",

            priority="MEDIUM"

        )
