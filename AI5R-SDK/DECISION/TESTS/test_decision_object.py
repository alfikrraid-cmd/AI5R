import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DECISION.decision_object import DecisionObject


def test_decision_object():
    decision = DecisionObject(
        context_id="CTX-001",
        objective="Choose best execution path",
        options=[
            {"option_id": "OPT-001", "score": 0.7},
            {"option_id": "OPT-002", "score": 0.9},
        ],
        selected_option={"option_id": "OPT-002", "score": 0.9},
        rationale="Highest score with acceptable risk",
        confidence_score=0.9,
        metadata={"owner": "AI5R"},
    )

    assert decision.object_type == "DECISION"
    assert decision.decision_id.startswith("DEC-")
    assert decision.context_id == "CTX-001"
    assert decision.status == "DECIDED"
    assert decision.selected_option["option_id"] == "OPT-002"
    assert decision.confidence_score == 0.9
    assert decision.metadata["owner"] == "AI5R"
