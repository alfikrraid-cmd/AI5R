from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class OpportunityRequest:

    industry: str
    problem: str
    goal: str
    deployment: str
    created_at: str = datetime.now(UTC).isoformat()



@dataclass
class OpportunityBlueprint:

    system_name: str
    agents: list[str]
    deployment: str



class OpportunityIntakeEngine:


    def analyze(
        self,
        request: OpportunityRequest
    ):


        return OpportunityBlueprint(

            system_name=
            f"{request.industry} AI OS",

            agents=[

                "ANALYST_AGENT",

                "WORKFLOW_AGENT",

                "ADVISOR_AGENT"

            ],

            deployment=
            request.deployment

        )
