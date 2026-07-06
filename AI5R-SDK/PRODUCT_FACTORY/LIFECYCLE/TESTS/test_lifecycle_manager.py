from PRODUCT_FACTORY.LIFECYCLE import (
    LifecycleManager,
)



def test_product_lifecycle():


    manager = LifecycleManager()


    product = manager.create(

        "UMKM-AI-001",

        "1.0.0"

    )


    assert product.state == "CREATED"


    state = manager.transition(

        "UMKM-AI-001",

        "ACTIVE"

    )


    assert state == "ACTIVE"
