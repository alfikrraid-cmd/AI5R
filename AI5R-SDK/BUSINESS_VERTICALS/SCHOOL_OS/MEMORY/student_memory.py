from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any



@dataclass
class StudentMemory:

    student_id: str
    category: str
    experience: dict[str, Any]
    created_at: str = datetime.now(UTC).isoformat()



class StudentLearningMemory:


    def __init__(self):

        self.memories = {}



    def store(
        self,
        memory: StudentMemory
    ):

        self.memories[
            memory.student_id
        ] = memory


        return {

            "status":"STORED",

            "student_id":
            memory.student_id

        }



    def recall(
        self,
        student_id: str
    ):

        return self.memories.get(
            student_id
        )



    def analyze_pattern(
        self,
        student_id: str
    ):


        memory = self.memories.get(
            student_id
        )


        if not memory:

            return {

                "status":"NOT_FOUND"

            }


        return {

            "status":"ANALYZED",

            "learning_style":
            "VISUAL"

        }
