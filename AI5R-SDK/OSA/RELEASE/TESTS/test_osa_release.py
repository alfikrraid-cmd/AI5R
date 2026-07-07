from OSA.RELEASE import (
    create_release,
)



def test_osa_release():


    release = create_release()


    assert release.name == "OSA SYSTEM FACTORY"


    assert release.version == "1.0.0"


    assert release.status == "FROZEN"


    assert len(
        release.capabilities
    ) == 8
