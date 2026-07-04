import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.observation_engine import ObservationEngine


def test_observation_engine_creates_observation_from_reality():
    engine = ObservationEngine()

    reality = {
        "object_id": "reality-001",
        "object_type": "reality",
        "asset": "P-101",
        "measurements": {
            "vibration": 11.2,
            "temperature": 92,
        },
        "findings": [
            "seal_leakage",
            "bearing_issue",
        ],
    }

    observation = engine.observe(reality)

    assert observation["object_type"] == "observation"
    assert observation["source_object_id"] == "reality-001"
    assert observation["facts"]["asset"] == "P-101"
    assert "high_vibration_observed" in observation["signals"]
    assert "high_temperature_observed" in observation["signals"]
    assert "seal_leakage_observed" in observation["signals"]


def test_observation_engine_rejects_non_reality_object():
    engine = ObservationEngine()

    invalid_input = {
        "object_type": "knowledge",
    }

    try:
        engine.observe(invalid_input)
        assert False
    except ValueError as error:
        assert str(error) == "Input must be a Reality Object"
