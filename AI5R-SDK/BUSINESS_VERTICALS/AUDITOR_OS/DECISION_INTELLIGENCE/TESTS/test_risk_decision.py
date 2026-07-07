from BUSINESS_VERTICALS.AUDITOR_OS.DECISION_INTELLIGENCE import (
    RiskDecisionEngine,
)



def test_risk_decision():


    engine = RiskDecisionEngine()


    result = engine.analyze(

        {

            "compliance_issue": True

        }

    )


    assert result.category == "COMPLIANCE_RISK"


    assert result.score == "HIGH"


    assert (
        "Resolve"
        in result.recommendation
    )
