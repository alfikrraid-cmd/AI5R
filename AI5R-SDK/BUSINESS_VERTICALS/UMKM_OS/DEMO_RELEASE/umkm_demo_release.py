from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class UMKMDemoRelease:

    name: str
    version: str
    status: str
    features: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_demo_release():

    return UMKMDemoRelease(

        name="AI5R UMKM OS DEMO",

        version="1.0.0",

        status="READY",

        features=[

            "PRODUCT_OVERVIEW",

            "LIVE_STATUS",

            "BUSINESS_AGENTS",

            "AI_ADVISOR",

            "EXECUTIVE_DASHBOARD"

        ]

    )
