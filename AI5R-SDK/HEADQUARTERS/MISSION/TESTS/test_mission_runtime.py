from HEADQUARTERS import (
    MissionIntakeEngine,
)

from HEADQUARTERS.MISSION.runtime import (
    MissionRuntime,
)


def test_mission_runtime():

    mission = MissionIntakeEngine().create(

        title="Build Restaurant ERP"

    )

    result = MissionRuntime().execute(

        mission

    )

    assert result["status"]=="MISSION_APPROVED"

    assert result["mission"].status=="APPROVED"

    assert result["meeting"].leader=="Raid"

    assert len(

        result["meeting"].opinions

    )==8

