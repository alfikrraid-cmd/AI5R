from OSA.GATEWAY.DISCOVERY import (
    OpportunityDiscoveryEngine,
    DiscoveryInput,
)



def test_opportunity_discovery():


    engine = OpportunityDiscoveryEngine()


    result = engine.discover(

        DiscoveryInput(

            industry="SCHOOL",

            users=[

                "TEACHER",

                "STUDENT"

            ],

            problem=
            "Teacher workload",

            goal=
            "Personalized learning",

            scale=500

        )

    )


    assert (
        result.recommended_system
        ==
        "AI5R SCHOOL OS"
    )


    assert len(
        result.agents_needed
    ) == 3
