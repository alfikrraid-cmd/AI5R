from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SalesRelease:

    name: str
    version: str
    status: str
    demo_features: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_sales_release():

    return SalesRelease(

        name="AI5R UMKM OS SALES DEMO",

        version="1.0.0",

        status="READY",

        demo_features=[

            "PRODUCT_OVERVIEW",

            "AI_ADVISOR",

            "EXECUTIVE_DASHBOARD",

            "OWNER_SIMULATION",

            "PRODUCT_STORY",

            "DEMO_ANALYTICS"

        ]

    )
