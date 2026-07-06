from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class ProductFactoryRelease:

    name: str
    version: str
    status: str
    components: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_release():

    return ProductFactoryRelease(

        name="AI5R PRODUCT FACTORY",

        version="1.0.0",

        status="FROZEN",

        components=[

            "RUNTIME",

            "CAPABILITY",

            "KNOWLEDGE",

            "AGENT",

            "WORKFLOW",

            "PACKAGING",

            "DEPLOYMENT",

            "LIFECYCLE",

            "MARKETPLACE"

        ]

    )
