import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AI5R-SDK"))

from PRODUCTS.LTSA_BRAIN.cognitive_context import EnterpriseCognitiveContext
from PRODUCTS.LTSA_BRAIN.cognitive_objects import RecommendationObject


def test_context_creation():
    context = EnterpriseCognitiveContext(
        mission_id="MISSION-001",
        metadata={"source": "unit-test"},
    )

    assert context.trace_id
    assert context.mission_id == "MISSION-001"
    assert context.metadata["source"] == "unit-test"
    assert context.reality is None
    assert context.learning is None
    assert context.history[0]["action"] == "context_created"


def test_context_set_and_get():
    context = EnterpriseCognitiveContext()

    context.set("reality", {"finding": "seal leak"})

    assert context.get("reality") == {"finding": "seal leak"}
    assert context.history[-1]["action"] == "reality_set"


def test_context_rejects_unknown_field():
    context = EnterpriseCognitiveContext()

    try:
        context.set("unknown", {})
        assert False
    except ValueError as error:
        assert "Unknown cognitive field" in str(error)


def test_context_supports_cognitive_object_snapshot():
    context = EnterpriseCognitiveContext()
    recommendation = RecommendationObject(
        recommendation={"action": "inspect pump"},
        trace_id=context.trace_id,
    )

    context.set("recommendation", recommendation)

    snapshot = context.to_dict()

    assert snapshot["recommendation"]["object_type"] == "recommendation_object"
    assert snapshot["recommendation"]["payload"]["recommendation"]["action"] == "inspect pump"


def test_context_to_json():
    context = EnterpriseCognitiveContext(mission_id="MISSION-JSON")
    context.set("decision", {"approved": True})

    data = context.to_json()

    assert "MISSION-JSON" in data
    assert "approved" in data


def test_context_merge_same_trace_id():
    context_a = EnterpriseCognitiveContext(trace_id="TRACE-001")
    context_b = EnterpriseCognitiveContext(trace_id="TRACE-001")

    context_a.set("reality", {"finding": "high vibration"})
    context_b.set("knowledge", {"matched_rule": "bearing-risk"})

    context_a.merge(context_b)

    assert context_a.reality == {"finding": "high vibration"}
    assert context_a.knowledge == {"matched_rule": "bearing-risk"}
    assert context_a.history[-1]["action"] == "context_merged"


def test_context_rejects_merge_different_trace_id():
    context_a = EnterpriseCognitiveContext(trace_id="TRACE-A")
    context_b = EnterpriseCognitiveContext(trace_id="TRACE-B")

    try:
        context_a.merge(context_b)
        assert False
    except ValueError as error:
        assert "different trace_id" in str(error)


def test_all_cognitive_fields_exist():
    context = EnterpriseCognitiveContext()

    for field in EnterpriseCognitiveContext.COGNITIVE_FIELDS:
        assert hasattr(context, field)
