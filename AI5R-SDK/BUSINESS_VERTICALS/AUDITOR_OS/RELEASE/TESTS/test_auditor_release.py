from BUSINESS_VERTICALS.AUDITOR_OS.RELEASE import (
    create_release,
)



def test_auditor_release():


    release = create_release()


    assert release.name == "AI5R AUDITOR OS"


    assert release.version == "1.0.0"


    assert release.status == "FROZEN"


    assert len(
        release.modules
    ) == 7
