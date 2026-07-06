from REALTIME_ENGINE.AGENT_BRIDGE import (
    AgentRuntimeBridge,
)


class MockAgent:

    def execute(self, task):

        return {
            "task": task,
            "done": True
        }


def test_agent_bridge():

    bridge = AgentRuntimeBridge()

    bridge.register_agent(
        "EMP-001",
        MockAgent()
    )


    result = bridge.dispatch(
        "EMP-001",
        {
            "command": "analyze_market"
        }
    )


    assert result["status"] == "EXECUTED"
    assert result["agent_id"] == "EMP-001"
