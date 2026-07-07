import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AI5R-SDK"))
sys.path.insert(0, str(ROOT / "CORE-SERVICES"))

from API import IntegrationRuntimeAPI


def test_integration_runtime_api_health():
    api = IntegrationRuntimeAPI()

    result = api.health()

    assert result["status"] == "OK"
    assert result["service"] == "AI5R Integration Runtime API"


def test_integration_runtime_api_runs_goal_to_studio_payload():
    api = IntegrationRuntimeAPI()

    payload = api.run_goal("GOAL-001")

    assert payload["type"] == "AI5R_STUDIO_LIVE_OPS_SNAPSHOT"
    assert payload["version"] == "1.0"
    assert payload["data"]["status"] == "LIVE"
    assert payload["data"]["goals"][0]["goal_id"] == "GOAL-001"
    assert payload["data"]["runtimes"][0]["runtime_id"] == "ORG-RUN-GOAL-001"
    assert payload["data"]["runtimes"][0]["status"] == "COMPLETED"
    assert payload["events"][0]["event_type"] == "GOAL_RECEIVED"
    assert payload["events"][-1]["event_type"] == "AUTONOMOUS_RUNTIME_COMPLETED"


def test_integration_runtime_api_requires_goal_id:
    api = IntegrationRuntimeAPI()

    try:
        api.run_goal("")
    except ValueError as error:
        assert str(error) == "goal_id is required"
    else:
        raise AssertionError("ValueError was not raised")
