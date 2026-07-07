from BUSINESS_VERTICALS.UMKM_OS.DECISION_INTELLIGENCE import (
    UMKMDecisionEngine,
)



def test_business_decision():


    engine = UMKMDecisionEngine()


    result = engine.analyze(

        {

            "sales_decline": True

        }

    )


    assert result["status"] == "GENERATED"

    assert result["priority"] == "HIGH"

    assert (
        "retention"
        in result["recommendation"]
    )
