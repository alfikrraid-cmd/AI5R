from BUSINESS_VERTICALS.SCHOOL_OS.MEMORY import (
    StudentLearningMemory,
    StudentMemory,
)



def test_student_memory():


    memory = StudentLearningMemory()


    result = memory.store(

        StudentMemory(

            student_id="STUDENT-001",

            category="MATHEMATICS",

            experience={

                "strength":
                "visual_learning",

                "challenge":
                "algebra"

            }

        )

    )


    assert result["status"] == "STORED"


    saved = memory.recall(
        "STUDENT-001"
    )


    assert saved.category == "MATHEMATICS"


    pattern = memory.analyze_pattern(
        "STUDENT-001"
    )


    assert pattern["learning_style"] == "VISUAL"
