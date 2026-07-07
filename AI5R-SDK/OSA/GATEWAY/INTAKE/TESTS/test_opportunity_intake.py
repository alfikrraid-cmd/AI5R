from OSA.GATEWAY.INTAKE import (
    OpportunityIntakeEngine,
    OpportunityRequest,
)



def test_opportunity_intake():


    engine = OpportunityIntakeEngine()


    result = engine.analyze(

        OpportunityRequest(

            industry="FILM",

            problem="Need AI film production system",

            goal="Create movie workflow",

            deployment="OWN_SERVER"

        )

    )


    assert (
        result.system_name
        ==
        "FILM AI OS"
    )


    assert len(
        result.agents
    ) == 3


    assert (
        result.deployment
        ==
        "OWN_SERVER"
    )
