from BUSINESS_VERTICALS.SCHOOL_OS.ADVISOR import (
    SchoolEducationAdvisor,
)



def test_education_advisor():


    advisor = SchoolEducationAdvisor()


    result = advisor.analyze(

        {

            "learning_issue": True

        }

    )


    assert result.priority == "HIGH"


    assert (
        "personalized"
        in result.insight
    )
