from BUSINESS_VERTICALS.AUDITOR_OS.PRODUCT import (
    AuditorProductFactory,
)



def test_auditor_product():


    product = AuditorProductFactory().create()


    assert product.name == "AI5R AUDITOR OS"


    assert len(
        product.agents
    ) == 3


    assert product.version == "1.0.0"


    assert (
        "RISK_DETECTION"
        in product.capabilities
    )
