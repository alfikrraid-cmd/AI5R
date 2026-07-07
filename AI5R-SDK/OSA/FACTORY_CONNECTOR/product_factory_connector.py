from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ProductBuildRequest:

    system_name: str
    agents: list[str]
    deployment: str
    created_at: str = datetime.now(UTC).isoformat()



class AI5RProductFactoryConnector:


    def submit(
        self,
        blueprint
    ):


        return ProductBuildRequest(

            system_name=
            blueprint.system_name,

            agents=
            blueprint.agents,

            deployment=
            blueprint.deployment

        )
