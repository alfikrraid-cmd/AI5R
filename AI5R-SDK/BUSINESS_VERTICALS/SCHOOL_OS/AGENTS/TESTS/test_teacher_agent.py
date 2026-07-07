from BUSINESS_VERTICALS.SCHOOL_OS.AGENTS import (
    TeacherAgentFactory,
)



def test_teacher_agent():


    agent = TeacherAgentFactory().create()


    assert agent.name == "AI5R Teacher Assistant"


    assert agent.role == "AI_TEACHING_PARTNER"


    assert len(
        agent.capabilities
    ) == 3
