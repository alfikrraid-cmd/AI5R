from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class PlatformRelease:

    name: str
    version: str
    status: str
    modules: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_release():

    return PlatformRelease(

        name="AI5R MULTI PRODUCT PLATFORM",

        version="1.0.0",

        status="FROZEN",

        modules=[

            "PRODUCT_CENTER",

            "LIFECYCLE",

            "DEPLOYMENT",

            "INTELLIGENCE",

            "COMMAND_CENTER",

            "MARKETPLACE",

            "PORTFOLIO",

            "RECOMMENDATION",

            "ROADMAP"

        ]

    )
