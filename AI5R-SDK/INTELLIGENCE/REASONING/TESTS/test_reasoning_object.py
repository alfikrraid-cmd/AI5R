import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_object import CanonicalObject
from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject


def test_reasoning_object_inherits_canonical_object():
    obj = ReasoningObject()

    assert isinstance(obj, CanonicalObject)
    assert obj.object_type == "REASONING_OBJECT"
    assert obj.reasoning_id.startswith("AI5R-REASONING_OBJECT-")


def test_reasoning_object_collects_reasoning():
    obj = ReasoningObject()

    obj.add_premise({"statement": "Demand is increasing"})
    obj.add_evidence({"source": "Sales Report"})
    obj.add_reasoning_step("Demand increased")
    obj.add_supporting_knowledge("KO-001")

    obj.set_conclusion(
        {"decision": "Increase production"},
        confidence=0.92,
    )

    assert len(obj.premises) == 1
    assert len(obj.evidence) == 1
    assert obj.reasoning_path[0] == "Demand increased"
    assert obj.supporting_knowledge[0] == "KO-001"
    assert obj.conclusion["decision"] == "Increase production"
    assert obj.confidence == 0.92


def test_reasoning_object_serialization():
    obj = ReasoningObject()

    obj.add_reasoning_step("Analyze trend")

    data = obj.to_dict()

    assert data["object_type"] == "REASONING_OBJECT"
    assert data["reasoning_path"][0] == "Analyze trend"
