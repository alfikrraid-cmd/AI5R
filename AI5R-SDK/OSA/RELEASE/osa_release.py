from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class OSARelease:

    name: str
    version: str
    status: str
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_release():

    return OSARelease(

        name="OSA SYSTEM FACTORY",

        version="1.0.0",

        status="FROZEN",

        capabilities=[

            "CUSTOMER_INTAKE",

            "OPPORTUNITY_DISCOVERY",

            "BUSINESS_REASONING",

            "SYSTEM_BLUEPRINT",

            "ARCHITECTURE_GENERATION",

            "PRODUCT_FACTORY_CONNECTOR",

            "WORKSPACE_GENERATION",

            "DEPLOYMENT_ORCHESTRATION"

        ]

    )
