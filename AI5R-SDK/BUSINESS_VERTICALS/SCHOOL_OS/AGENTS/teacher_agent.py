from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class TeacherAgent:

    agent_id: str
    name: str
    role: str
    capabilities: list[str]
    created_at: str = datetime.now(UTC).isoformat()



class TeacherAgentFactory:


    def create(self):

        return TeacherAgent(

            agent_id="TEACHER-001",

            name="AI5R Teacher Assistant",

            role="AI_TEACHING_PARTNER",

            capabilities=[

                "LESSON_PLANNING",

                "CURRICULUM_SUPPORT",

                "ASSESSMENT_DESIGN"

            ]

        )
