import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DECISION.decision_policy_engine import DecisionPolicyEngine


def test_policy_engine():

    engine = DecisionPolicyEngine()

    result = engine.evaluate(
        [
            {
                "option_id":"A",
                "score":0.95,
                "allowed":False,
            },
            {
                "option_id":"B",
                "score":0.70,
                "allowed":True,
            },
        ]
    )

    assert result["status"] == "APPROVED"
    assert len(result["approved_options"]) == 1
    assert result["approved_options"][0]["option_id"] == "B"
