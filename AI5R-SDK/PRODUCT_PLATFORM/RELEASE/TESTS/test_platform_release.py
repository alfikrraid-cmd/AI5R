from PRODUCT_PLATFORM.RELEASE import (
    create_release,
)



def test_platform_release():


    release = create_release()


    assert release.name == "AI5R MULTI PRODUCT PLATFORM"


    assert release.version == "1.0.0"


    assert release.status == "FROZEN"


    assert len(
        release.modules
    ) == 9
