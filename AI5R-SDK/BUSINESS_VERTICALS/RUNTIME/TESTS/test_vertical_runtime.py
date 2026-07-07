from BUSINESS_VERTICALS.RUNTIME import (
    VerticalRuntime,
    BusinessVertical,
)



def test_vertical_registration():


    runtime = VerticalRuntime()


    result = runtime.register(

        BusinessVertical(

            vertical_id="UMKM-OS",

            name="AI5R UMKM OS",

            domain="BUSINESS",

            agents=[

                "MARKETING_AGENT",

                "SALES_AGENT"

            ],

            capabilities=[

                "MARKET_ANALYSIS",

                "CUSTOMER_ANALYSIS"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    vertical = runtime.get(
        "UMKM-OS"
    )


    assert vertical.domain == "BUSINESS"
