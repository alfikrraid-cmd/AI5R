from BUSINESS_VERTICALS.AUDITOR_OS.AGENTS import (
    AuditorAgentFactory,
)



def test_auditor_agent():


    agent = AuditorAgentFactory().create()


    assert agent.name == "AI5R Auditor Agent"


    assert agent.role == "DIGITAL_AUDIT_ASSISTANT"


    assert len(
        agent.capabilities
    ) == 4


    assert (
        "RISK_ANALYSIS"
        in agent.capabilities
    )
