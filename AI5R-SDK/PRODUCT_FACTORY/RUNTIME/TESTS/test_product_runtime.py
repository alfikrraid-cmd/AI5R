from PRODUCT_FACTORY.RUNTIME import (
    ProductRuntime,
    AIProductManifest,
)



def test_product_registration():


    factory = ProductRuntime()


    product = AIProductManifest(

        product_id="UMKM-AI-001",

        name="UMKM Assistant",

        domain="BUSINESS",

        capabilities=[

            "MARKETING",

            "SALES"

        ]

    )


    result = factory.register(product)


    assert result["status"] == "REGISTERED"


    saved = factory.get_product(
        "UMKM-AI-001"
    )


    assert saved.name == "UMKM Assistant"
