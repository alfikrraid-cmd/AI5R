from BUSINESS_VERTICALS.UMKM_OS.DEMO_RELEASE import (
    create_demo_release,
)



def test_demo_release():


    release = create_demo_release()


    assert release.name == "AI5R UMKM OS DEMO"


    assert release.version == "1.0.0"


    assert release.status == "READY"


    assert len(
        release.features
    ) == 5
