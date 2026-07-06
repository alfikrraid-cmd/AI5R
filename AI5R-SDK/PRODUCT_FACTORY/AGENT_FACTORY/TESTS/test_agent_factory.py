from PRODUCT_FACTORY.AGENT_FACTORY import (
    AgentFactory,
    ProductAgent,
)



def test_agent_creation():


    factory = AgentFactory()


    result = factory.create(

        ProductAgent(

            agent_id="AGENT-MARKETING-001",

            product_id="UMKM-AI-001",

            role="MARKETING"

        )

    )


    assert result["status"] == "CREATED"


    agent = factory.get(
        "AGENT-MARKETING-001"
    )


    assert agent.role == "MARKETING"
