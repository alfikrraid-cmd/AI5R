from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from BRAIN.REASONING import ReasoningEngine


def test_reasoning_safe():
    engine = ReasoningEngine()

    result = engine.think({"task": "run"})

    assert result.output == "APPROVE"


def test_reasoning_risk():
    engine = ReasoningEngine()

    result = engine.think({"risk": "high"})

    assert result.output == "REJECT"
    assert result.confidence > 0.9
