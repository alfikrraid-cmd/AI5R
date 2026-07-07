from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class UMKMProduct:

    product_id: str
    name: str
    agents: list[str]
    capabilities: list[str]
    version: str
    created_at: str = datetime.now(UTC).isoformat()



class UMKMOSFactory:


    def create(self):

        return UMKMProduct(

            product_id="UMKM-OS-001",

            name="AI5R UMKM OS",

            agents=[

                "BUSINESS_ANALYST",

                "MARKETING_AGENT",

                "SALES_AGENT",

                "FINANCE_AGENT",

                "GROWTH_AGENT"

            ],

            capabilities=[

                "MARKET_ANALYSIS",

                "CONTENT_PLANNING",

                "CUSTOMER_ANALYSIS",

                "FINANCIAL_TRACKING",

                "GROWTH_RECOMMENDATION"

            ],

            version="1.0.0"

        )
