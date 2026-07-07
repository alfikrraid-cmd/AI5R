from OSA.FACTORY_CONNECTOR import (
    AI5RProductFactoryConnector,
)


from OSA.GATEWAY.BLUEPRINT import (
    SystemBlueprintGenerator,
)



def test_factory_connector():


    blueprint = SystemBlueprintGenerator().generate(

        industry="FILM",

        deployment="OWN_SERVER"

    )


    connector = AI5RProductFactoryConnector()


    request = connector.submit(
        blueprint
    )


    assert (
        request.system_name
        ==
        "AI5R FILM OS"
    )


    assert len(
        request.agents
    ) == 3


    assert (
        request.deployment
        ==
        "OWN_SERVER"
    )
