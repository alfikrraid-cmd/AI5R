from HEADQUARTERS import (

ExecutiveBoardFactory,

ExecutiveMeetingRuntime,

MissionIntakeEngine,

)

from HEADQUARTERS.LEARNING import LearningEngine


def test_learning_engine():

    board=ExecutiveBoardFactory().create()

    meeting=ExecutiveMeetingRuntime(

        board

    ).run(

        "Build ERP"

    )

    mission=MissionIntakeEngine().create(

        title="Build ERP"

    )

    mission.approve(

        "APPROVED"

    )

    experiences=LearningEngine().learn(

        mission,

        meeting,

    )

    assert len(experiences)==8

    assert experiences[0].experience_id.startswith(

        "EXP-"

    )

    assert experiences[0].outcome=="APPROVED"

