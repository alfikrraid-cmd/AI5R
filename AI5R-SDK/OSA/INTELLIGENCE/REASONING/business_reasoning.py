from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class OpportunityAssessment:

    score: str
    opportunity: str
    recommendation: str
    created_at: str = datetime.now(UTC).isoformat()



class BusinessReasoningEngine:


    def evaluate(
        self,
        idea: str
    ):


        keywords = idea.lower()


        if (
            "ai"
            in keywords
            or
            "system"
            in keywords
        ):


            return OpportunityAssessment(

                score="HIGH",

                opportunity=
                "AI transformation opportunity",

                recommendation=
                "Build specialized AI operating system"

            )


        return OpportunityAssessment(

            score="MEDIUM",

            opportunity=
            "Business opportunity detected",

            recommendation=
            "Perform deeper market analysis"

        )
