from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SystemBlueprint:

    system_name: str
    agents: list[str]
    workflow: list[str]
    deployment: str
    created_at: str = datetime.now(UTC).isoformat()



class SystemBlueprintGenerator:


    def generate(
        self,
        industry: str,
        deployment: str
    ):


        return SystemBlueprint(

            system_name=
            f"AI5R {industry} OS",

            agents=[

                "ANALYST_AGENT",

                "WORKFLOW_AGENT",

                "ADVISOR_AGENT"

            ],

            workflow=[

                "INPUT_ANALYSIS",

                "SYSTEM_EXECUTION",

                "RESULT_DELIVERY"

            ],

            deployment=deployment

        )
