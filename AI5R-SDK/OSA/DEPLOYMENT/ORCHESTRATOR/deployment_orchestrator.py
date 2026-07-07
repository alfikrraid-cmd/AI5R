from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class DeploymentPlan:

    system_name: str
    deployment_mode: str
    domain: str
    created_at: str = datetime.now(UTC).isoformat()



class DeploymentOrchestrator:


    def create_plan(
        self,
        system_name: str,
        mode: str,
        domain: str
    ):


        return DeploymentPlan(

            system_name=
            system_name,

            deployment_mode=
            mode,

            domain=
            domain

        )
