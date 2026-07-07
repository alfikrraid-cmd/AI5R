from OSA.GATEWAY.BLUEPRINT import (
    SystemBlueprintGenerator,
)



def test_system_blueprint():


    generator = SystemBlueprintGenerator()


    blueprint = generator.generate(

        industry="FILM",

        deployment="OWN_SERVER"

    )


    assert (
        blueprint.system_name
        ==
        "AI5R FILM OS"
    )


    assert len(
        blueprint.agents
    ) == 3


    assert (
        blueprint.deployment
        ==
        "OWN_SERVER"
    )
