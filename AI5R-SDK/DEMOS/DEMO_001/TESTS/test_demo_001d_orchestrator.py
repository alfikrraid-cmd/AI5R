from DEMOS.DEMO_001.login_api_demo import run_demo


def test_demo_001d_uses_mission_orchestrator_lifecycle():
    result = run_demo()
    logs = "\n".join(result["logs"])

    assert "Mission Orchestrator completed employee lifecycle" in logs
    assert "Runtime phases: RECEIVED" in logs
    assert len(result["activity_stream"]) == 5


def test_demo_001d_selects_api_capability():
    result = run_demo()
    logs = "\n".join(result["logs"])

    assert "Selected capabilities: API" in logs
