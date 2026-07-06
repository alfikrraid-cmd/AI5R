import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DECISION.decision_engine import DecisionEngine
from DECISION.decision_registry import DecisionRegistry


def test_decision_registry():

    engine = DecisionEngine()
    registry = DecisionRegistry()

    decision = engine.decide(
        context_id="CTX-001",
        objective="Choose",
        options=[
            {"option_id":"A","score":0.3},
            {"option_id":"B","score":0.9},
        ],
    )

    registration = registry.register(decision)

    assert registration["status"] == "REGISTERED"
    assert registry.get(decision.decision_id) == decision
    assert registry.list_all() == [decision]
    assert registry.list_by_context("CTX-001") == [decision]
    assert registry.list_by_status("DECIDED") == [decision]
