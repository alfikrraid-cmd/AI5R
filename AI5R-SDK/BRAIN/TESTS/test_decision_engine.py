import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine
from BRAIN.hypothesis_engine import HypothesisEngine
from BRAIN.decision_engine import DecisionEngine


def test_decision_engine_selects_best_hypothesis():

    reality = {
        "object_id": "reality-005",
        "object_type": "reality",
        "asset": "pump-001",
        "measurements": {
            "vibration": 12,
            "temperature": 95,
        },
        "findings": ["leak"],
    }

    observation = ObservationEngine().observe(reality)

    understanding = UnderstandingEngine().understand(observation)

    hypothesis = HypothesisEngine().hypothesize(understanding)

    decision = DecisionEngine().decide(hypothesis)

    assert decision.status == "decided"

    assert decision.selected_hypothesis["confidence"] == max(
        h["confidence"]
        for h in hypothesis.hypotheses
    )

    assert decision.enterprise_context["stage"] == "decision"

    assert decision.digital_thread_id == "reality-005"


def test_decision_object_to_dict():

    reality = {
        "object_id": "reality-006",
        "object_type": "reality",
        "asset": "motor-001",
        "measurements": {
            "vibration": 5,
            "temperature": 70,
        },
        "findings": [],
    }

    observation = ObservationEngine().observe(reality)

    understanding = UnderstandingEngine().understand(observation)

    hypothesis = HypothesisEngine().hypothesize(understanding)

    decision = DecisionEngine().decide(hypothesis)

    data = decision.to_dict()

    assert data["status"] == "decided"
    assert data["enterprise_context"]["derived_from"] == "hypothesis"
