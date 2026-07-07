from BUSINESS_VERTICALS.SCHOOL_OS.RUNTIME import (
    SchoolRuntime,
    SchoolVertical,
)



def test_school_runtime():


    runtime = SchoolRuntime()


    result = runtime.register(

        SchoolVertical(

            vertical_id="SCHOOL-OS",

            name="AI5R SCHOOL OS",

            domain="EDUCATION",

            agents=[

                "CURRICULUM_AGENT",

                "TEACHER_AGENT",

                "STUDENT_AGENT"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    school = runtime.get(
        "SCHOOL-OS"
    )


    assert school.domain == "EDUCATION"


    assert len(
        school.agents
    ) == 3
