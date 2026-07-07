from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class ComplianceAdvice:

    insight: str
    recommendation: str
    priority: str
    created_at: str = datetime.now(UTC).isoformat()



class ComplianceAdvisor:


    def analyze(
        self,
        data: dict[str, Any]
    ):


        if data.get(
            "compliance_risk"
        ):


            return ComplianceAdvice(

                insight=
                "Compliance weakness detected",

                recommendation=
                "Improve documentation and compliance process",

                priority=
                "HIGH"

            )


        return ComplianceAdvice(

            insight=
            "Compliance condition stable",

            recommendation=
            "Continue regular monitoring",

            priority=
            "MEDIUM"

        )
