from OSA.ARCHITECTURE.GENERATOR import (
    ArchitectureGenerator,
)



def test_architecture_generator():


    generator = ArchitectureGenerator()


    architecture = generator.generate(

        system_name="AI5R FILM OS",

        deployment="OWN_SERVER"

    )


    assert (
        architecture.system_name
        ==
        "AI5R FILM OS"
    )


    assert (
        architecture.backend
        ==
        "Agent Runtime API"
    )


    assert len(
        architecture.agents
    ) == 3


    assert (
        architecture.deployment
        ==
        "OWN_SERVER"
    )
