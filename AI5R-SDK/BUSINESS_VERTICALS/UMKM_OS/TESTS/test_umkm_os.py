from BUSINESS_VERTICALS.UMKM_OS import (
    UMKMOSFactory,
)



def test_umkm_product():


    product = UMKMOSFactory().create()


    assert product.name == "AI5R UMKM OS"


    assert len(
        product.agents
    ) == 5


    assert product.version == "1.0.0"
