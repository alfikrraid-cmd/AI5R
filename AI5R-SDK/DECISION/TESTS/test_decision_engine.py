import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DECISION.decision_engine import DecisionEngine


def test_decision_engine():

    engine = DecisionEngine()

    decision = engine.decide(
        context_id="CTX-001",
        objective="Select execution path",
        options=[
            {"option_id": "A", "score": 0.55},
            {"option_id": "B", "score": 0.91},
            {"option_id": "C", "score": 0.72},
        ],
        metadata={
            "owner": "AI5R",
        },
    )

    assert decision.object_type == "DECISION"
    assert decision.selected_option["option_id"] == "B"
    assert decision.confidence_score == 0.91
    assert decision.status == "DECIDED"
