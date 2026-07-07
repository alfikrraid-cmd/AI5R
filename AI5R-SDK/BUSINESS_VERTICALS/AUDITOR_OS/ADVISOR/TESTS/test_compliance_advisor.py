from BUSINESS_VERTICALS.AUDITOR_OS.ADVISOR import (
    ComplianceAdvisor,
)



def test_compliance_advisor():


    advisor = ComplianceAdvisor()


    result = advisor.analyze(

        {

            "compliance_risk": True

        }

    )


    assert result.priority == "HIGH"


    assert (
        "Compliance"
        in result.insight
    )
