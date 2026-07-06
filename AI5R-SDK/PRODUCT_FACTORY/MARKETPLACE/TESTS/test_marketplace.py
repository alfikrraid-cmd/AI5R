from PRODUCT_FACTORY.MARKETPLACE import (
    MarketplaceRegistry,
    MarketplaceProduct,
)



def test_marketplace_publish():


    registry = MarketplaceRegistry()


    result = registry.publish(

        MarketplaceProduct(

            product_id="UMKM-AI-001",

            name="UMKM Assistant AI",

            domain="BUSINESS",

            version="1.0.0"

        )

    )


    assert result["status"] == "PUBLISHED"


    product = registry.get(
        "UMKM-AI-001"
    )


    assert product.domain == "BUSINESS"
