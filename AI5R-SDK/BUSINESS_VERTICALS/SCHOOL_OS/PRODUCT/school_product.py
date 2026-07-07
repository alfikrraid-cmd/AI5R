from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SchoolProduct:

    product_id: str
    name: str
    agents: list[str]
    capabilities: list[str]
    version: str
    created_at: str = datetime.now(UTC).isoformat()



class SchoolProductFactory:


    def create(self):

        return SchoolProduct(

            product_id="SCHOOL-OS-001",

            name="AI5R SCHOOL OS",

            agents=[

                "CURRICULUM_AGENT",

                "TEACHER_ASSISTANT_AGENT",

                "STUDENT_MENTOR_AGENT",

                "SCHOOL_MANAGEMENT_AGENT"

            ],

            capabilities=[

                "CURRICULUM_DESIGN",

                "LESSON_PLANNING",

                "STUDENT_ANALYSIS",

                "SCHOOL_MANAGEMENT"

            ],

            version="1.0.0"

        )
