from BUSINESS_VERTICALS.UMKM_OS.AGENTS import (
    UMKMAgentRegistry,
    UMKMAgentConfig,
)



def test_umkm_agent_config():


    registry = UMKMAgentRegistry()


    result = registry.register(

        UMKMAgentConfig(

            agent_id="MARKETING-001",

            role="Growth Marketing Specialist",

            goal="Increase customer acquisition",

            knowledge_domain="UMKM-MARKETING",

            workflow="CAMPAIGN_PLANNING"

        )

    )


    assert result["status"] == "REGISTERED"


    agent = registry.get(
        "MARKETING-001"
    )


    assert agent.role == "Growth Marketing Specialist"
