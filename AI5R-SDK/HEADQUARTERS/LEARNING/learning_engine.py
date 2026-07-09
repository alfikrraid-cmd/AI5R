from HEADQUARTERS.LEARNING.experience import Experience


class LearningEngine:

    def learn(

        self,

        mission,

        meeting,

    ):

        experiences=[]

        for opinion in meeting.opinions:

            experiences.append(

                Experience(

                    mission_id=mission.mission_id,

                    executive=opinion.executive_name,

                    lesson=opinion.recommendation,

                    outcome=mission.status,

                    confidence=opinion.confidence,

                )

            )

        return experiences

