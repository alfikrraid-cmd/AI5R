import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DECISION.decision_runtime import DecisionRuntime


def test_decision_runtime():

    runtime = DecisionRuntime()

    result = runtime.create(
        context_id="CTX-001",
        objective="Select execution",
        options=[
            {"option_id":"A","score":0.42},
            {"option_id":"B","score":0.88},
        ],
        metadata={
            "owner":"AI5R"
        },
    )

    decision = result["decision"]

    assert result["status"] == "CREATED"
    assert result["registration"]["status"] == "REGISTERED"

    assert runtime.get(decision.decision_id) == decision
    assert runtime.list_all() == [decision]
    assert runtime.list_by_context("CTX-001") == [decision]
    assert runtime.list_by_status("DECIDED") == [decision]
