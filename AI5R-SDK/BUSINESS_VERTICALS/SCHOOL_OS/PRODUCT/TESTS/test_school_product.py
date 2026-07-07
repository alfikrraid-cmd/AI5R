from BUSINESS_VERTICALS.SCHOOL_OS.PRODUCT import (
    SchoolProductFactory,
)



def test_school_product():


    product = SchoolProductFactory().create()


    assert product.name == "AI5R SCHOOL OS"


    assert len(
        product.agents
    ) == 4


    assert product.version == "1.0.0"
