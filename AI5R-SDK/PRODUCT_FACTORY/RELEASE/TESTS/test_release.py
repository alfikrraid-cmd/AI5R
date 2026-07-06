from PRODUCT_FACTORY.RELEASE import (
    create_release,
)



def test_product_factory_release():


    release = create_release()


    assert release.version == "1.0.0"

    assert release.status == "FROZEN"

    assert len(
        release.components
    ) == 9
