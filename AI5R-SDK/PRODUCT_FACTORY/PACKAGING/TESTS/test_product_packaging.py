from PRODUCT_FACTORY.PACKAGING import (
    ProductPackager,
    ProductPackage,
)



def test_product_packaging():


    packager = ProductPackager()


    package = ProductPackage(

        product_id="UMKM-AI-001",

        manifest={
            "name":"UMKM Assistant"
        },

        agents=[

            "MARKETING_AGENT"

        ],

        capabilities=[

            "MARKET_ANALYSIS"

        ],

        workflow_id="WF-001",

        version="1.0.0"

    )


    result = packager.package(
        package
    )


    assert result["status"] == "PACKAGED"


    assert packager.release_ready(
        "UMKM-AI-001"
    )
