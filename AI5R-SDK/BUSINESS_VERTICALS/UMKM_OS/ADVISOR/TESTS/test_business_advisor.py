from BUSINESS_VERTICALS.UMKM_OS.ADVISOR import (
    UMKMBusinessAdvisor,
)



def test_business_advisor():


    advisor = UMKMBusinessAdvisor()


    result = advisor.analyze(

        {

            "sales_decline": True

        }

    )


    assert result.priority == "HIGH"


    assert (
        "retention"
        in result.recommendation
    )
