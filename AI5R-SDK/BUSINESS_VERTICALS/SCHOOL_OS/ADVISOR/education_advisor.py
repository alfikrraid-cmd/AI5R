from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class EducationAdvice:

    insight: str
    recommendation: str
    priority: str
    created_at: str = datetime.now(UTC).isoformat()



class SchoolEducationAdvisor:


    def analyze(
        self,
        data: dict[str, Any]
    ):


        if data.get(
            "learning_issue"
        ):


            return EducationAdvice(

                insight=
                "Student requires personalized learning support",

                recommendation=
                "Adjust learning method and create targeted exercise",

                priority="HIGH"

            )


        return EducationAdvice(

            insight=
            "Learning progress is stable",

            recommendation=
            "Continue current learning strategy",

            priority="MEDIUM"

        )
