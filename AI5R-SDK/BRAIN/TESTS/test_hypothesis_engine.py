import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine
from BRAIN.hypothesis_engine import HypothesisEngine


def test_hypothesis_engine_creates_hypotheses_from_understanding():
    reality = {
        "object_id": "reality-003",
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

    names = [item["name"] for item in hypothesis.hypotheses]

    assert hypothesis.understanding_id == understanding.understanding_id
    assert hypothesis.digital_thread_id == "reality-003"
    assert hypothesis.status == "hypothesized"
    assert hypothesis.selected is False
    assert "mechanical_instability" in names
    assert "thermal_stress" in names
    assert "seal_or_fluid_integrity_issue" in names
    assert hypothesis.enterprise_context["derived_from"] == "understanding"


def test_hypothesis_object_can_convert_to_dict():
    reality = {
        "object_id": "reality-004",
        "object_type": "reality",
        "asset": "motor-001",
        "measurements": {
            "vibration": 4,
            "temperature": 60,
        },
        "findings": [],
    }

    observation = ObservationEngine().observe(reality)
    understanding = UnderstandingEngine().understand(observation)
    hypothesis = HypothesisEngine().hypothesize(understanding)

    data = hypothesis.to_dict()

    assert data["understanding_id"] == understanding.understanding_id
    assert data["digital_thread_id"] == "reality-004"
    assert data["enterprise_context"]["stage"] == "hypothesis"
    assert len(data["hypotheses"]) >= 1
