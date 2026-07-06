from OS import (
    AgentRuntimeState,
    MultiAgentRuntime,
)


def test_register_agent():
    runtime = MultiAgentRuntime()

    agent = runtime.register_agent("EMP-001")

    assert agent.agent_id == "EMP-001"
    assert agent.state == AgentRuntimeState.IDLE


def test_start_agent():
    runtime = MultiAgentRuntime()

    agent = runtime.start_agent("EMP-001")

    assert agent.state == AgentRuntimeState.RUNNING


def test_send_message():
    runtime = MultiAgentRuntime()

    runtime.start_agent("EMP-001")
    runtime.start_agent("EMP-002")

    runtime.send_message(
        "EMP-001",
        "EMP-002",
    )

    assert runtime.get_agent(
        "EMP-002"
    ).inbox_size == 1


def test_process_message():
    runtime = MultiAgentRuntime()

    runtime.start_agent("EMP-001")
    runtime.start_agent("EMP-002")

    runtime.send_message(
        "EMP-001",
        "EMP-002",
    )

    runtime.process_next("EMP-002")

    receiver = runtime.get_agent("EMP-002")

    assert receiver.inbox_size == 0
    assert receiver.processed_messages == 1


def test_snapshot():
    runtime = MultiAgentRuntime()

    runtime.register_agent("EMP-001")

    snapshot = runtime.snapshot()

    assert "EMP-001" in snapshot
