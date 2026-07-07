from BUSINESS_VERTICALS.SCHOOL_OS.DECISION_INTELLIGENCE import (
    SchoolDecisionEngine,
)



def test_education_decision():


    engine = SchoolDecisionEngine()


    result = engine.analyze(

        {

            "learning_decline": True

        }

    )


    assert result["status"] == "GENERATED"


    assert result["priority"] == "HIGH"


    assert (
        "remediation"
        in result["recommendation"]
    )
