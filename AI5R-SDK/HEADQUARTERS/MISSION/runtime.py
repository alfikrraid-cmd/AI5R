from HEADQUARTERS import (
    ExecutiveBoardFactory,
    ExecutiveMeetingRuntime,
)

from HEADQUARTERS.MISSION import (
    Mission,
)


class MissionRuntime:

    def __init__(self):

        self.board = ExecutiveBoardFactory().create()

        self.meeting = ExecutiveMeetingRuntime(
            self.board
        )

    def execute(
        self,
        mission: Mission,
    ):

        meeting = self.meeting.run(
            mission.title
        )

        mission.assign_executive_review(
            leader=meeting.leader,
            participants=[
                opinion.executive_name
                for opinion in meeting.opinions
            ],
        )

        mission.approve(
            meeting.final_recommendation
        )

        return {

            "status":"MISSION_APPROVED",

            "mission":mission,

            "meeting":meeting,

        }
