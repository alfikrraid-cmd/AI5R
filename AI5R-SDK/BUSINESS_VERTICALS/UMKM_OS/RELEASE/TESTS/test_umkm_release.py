from BUSINESS_VERTICALS.UMKM_OS.RELEASE import (
    create_release,
)



def test_umkm_release():


    release = create_release()


    assert release.name == "AI5R UMKM OS"


    assert release.version == "1.0.0"


    assert release.status == "FROZEN"


    assert len(
        release.modules
    ) == 8
