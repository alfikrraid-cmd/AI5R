import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AI5R-SDK"))

from PRODUCTS.LTSA_BRAIN.cognitive_objects import (
    CognitiveObject,
    RecommendationObject,
    DecisionObject,
    PlanObject,
    ExecutionObject,
    LearningObject,
)


def test_cognitive_object_contract():
    obj = CognitiveObject(metadata={"source": "test"})

    assert obj.id
    assert obj.object_type == "cognitive_object"
    assert obj.version == "1.0"
    assert obj.created_at
    assert obj.metadata["source"] == "test"
    assert obj.trace_id == obj.id
    assert obj.parent_id is None
    assert obj.children == []
    assert len(obj.history) == 1


def test_digital_thread_child_support():
    parent = CognitiveObject()
    child = CognitiveObject(parent_id=parent.id, trace_id=parent.trace_id)

    parent.add_child(child)

    assert child.parent_id == parent.id
    assert child.trace_id == parent.trace_id
    assert child.id in parent.children
    assert parent.history[-1]["action"] == "child_added"


def test_recommendation_object():
    obj = RecommendationObject(recommendation={"action": "repair"})

    assert obj.object_type == "recommendation_object"
    assert obj.payload["recommendation"]["action"] == "repair"


def test_decision_object():
    obj = DecisionObject(decision={"approved": True})

    assert obj.object_type == "decision_object"
    assert obj.payload["decision"]["approved"] is True


def test_plan_object():
    obj = PlanObject(plan={"steps": ["inspect", "repair"]})

    assert obj.object_type == "plan_object"
    assert obj.payload["plan"]["steps"] == ["inspect", "repair"]


def test_execution_object():
    obj = ExecutionObject(execution={"status": "queued"})

    assert obj.object_type == "execution_object"
    assert obj.payload["execution"]["status"] == "queued"


def test_learning_object():
    obj = LearningObject(learning={"lesson": "seal failure pattern"})

    assert obj.object_type == "learning_object"
    assert obj.payload["learning"]["lesson"] == "seal failure pattern"


def test_to_dict_contains_enterprise_fields():
    obj = CognitiveObject()
    data = obj.to_dict()

    required = [
        "id",
        "object_type",
        "version",
        "created_at",
        "metadata",
        "trace_id",
        "parent_id",
        "children",
        "history",
        "payload",
    ]

    for field in required:
        assert field in data
