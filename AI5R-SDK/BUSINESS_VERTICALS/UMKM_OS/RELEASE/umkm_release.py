from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class UMKMRelease:

    name: str
    version: str
    status: str
    modules: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_release():

    return UMKMRelease(

        name="AI5R UMKM OS",

        version="1.0.0",

        status="FROZEN",

        modules=[

            "PRODUCT",

            "KNOWLEDGE",

            "AGENT",

            "WORKFLOW",

            "DECISION",

            "MEMORY",

            "ADVISOR",

            "RUNTIME"

        ]

    )
