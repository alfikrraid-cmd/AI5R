from PRODUCT_FACTORY.CAPABILITY import (
    CapabilityRegistry,
    Capability,
)



def test_capability_registration():


    registry = CapabilityRegistry()


    capability = Capability(

        capability_id="CAP-MARKET",

        name="Market Research",

        description="Analyze market opportunity"

    )


    result = registry.register(
        capability
    )


    assert result["status"] == "REGISTERED"


    saved = registry.get(
        "CAP-MARKET"
    )


    assert saved.name == "Market Research"
