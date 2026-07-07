from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SystemArchitecture:

    system_name: str
    frontend: str
    backend: str
    database: str
    agents: list[str]
    deployment: str
    created_at: str = datetime.now(UTC).isoformat()



class ArchitectureGenerator:


    def generate(
        self,
        system_name: str,
        deployment: str
    ):


        return SystemArchitecture(

            system_name=
            system_name,

            frontend=
            "AI Dashboard",

            backend=
            "Agent Runtime API",

            database=
            "Knowledge Memory Store",

            agents=[

                "PLANNER_AGENT",

                "EXECUTION_AGENT",

                "ADVISOR_AGENT"

            ],

            deployment=
            deployment

        )
