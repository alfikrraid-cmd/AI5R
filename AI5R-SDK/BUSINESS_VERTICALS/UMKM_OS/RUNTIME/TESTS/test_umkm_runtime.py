from BUSINESS_VERTICALS.UMKM_OS.RUNTIME import (
    AI5RUMKMOSRuntime,
)



def test_umkm_runtime():


    runtime = AI5RUMKMOSRuntime()


    result = runtime.start(

        {

            "product":
            "AI5R UMKM OS",

            "agents":[

                "MARKETING",

                "SALES",

                "FINANCE"

            ]

        }

    )


    assert result["status"] == "STARTED"


    assert runtime.health() == "ACTIVE"
