from dataclasses import dataclass
from datetime import datetime, UTC



@dataclass
class SchoolRelease:

    name: str
    version: str
    status: str
    modules: list[str]
    created_at: str = datetime.now(UTC).isoformat()



def create_release():

    return SchoolRelease(

        name="AI5R SCHOOL OS",

        version="1.0.0",

        status="FROZEN",

        modules=[

            "KNOWLEDGE_DOMAIN",

            "TEACHER_AGENT",

            "LEARNING_WORKFLOW",

            "DECISION_INTELLIGENCE",

            "STUDENT_MEMORY",

            "EDUCATION_ADVISOR",

            "RUNTIME_INTEGRATION"

        ]

    )
