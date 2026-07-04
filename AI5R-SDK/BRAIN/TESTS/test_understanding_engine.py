import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine
from BRAIN.understanding_engine import UnderstandingEngine


def test_understanding_engine_creates_understanding_from_observation():
    reality = {
        "object_id": "reality-001",
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

    assert understanding.observation_id == "obs-reality-001"
    assert understanding.digital_thread_id == "reality-001"
    assert understanding.confidence > 0
    assert "high_vibration_observed" in understanding.meaning
    assert "high_temperature_observed" in understanding.meaning
    assert understanding.enterprise_context["stage"] == "understanding"


def test_understanding_object_can_convert_to_dict():
    reality = {
        "object_id": "reality-002",
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

    data = understanding.to_dict()

    assert data["observation_id"] == "obs-reality-002"
    assert data["digital_thread_id"] == "reality-002"
    assert data["enterprise_context"]["derived_from"] == "observation"
