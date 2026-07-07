from OSA.INTELLIGENCE.REASONING import (
    BusinessReasoningEngine,
)



def test_business_reasoning():


    engine = BusinessReasoningEngine()


    result = engine.evaluate(

        "Create AI film production system"

    )


    assert result.score == "HIGH"


    assert (
        "AI"
        in result.opportunity
    )


    assert (
        "operating"
        in result.recommendation
    )
