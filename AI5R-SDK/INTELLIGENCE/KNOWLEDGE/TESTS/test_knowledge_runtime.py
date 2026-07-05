import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.RUNTIME.knowledge_runtime import KnowledgeRuntime


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_knowledge_runtime_processes_object():
    runtime = KnowledgeRuntime()

    knowledge = KnowledgeObject(
        knowledge_id="KO-R001",
        summary="UMKM needs pricing strategy to increase revenue",
        metadata={
            "impact": 0.9,
            "urgency": 0.8,
            "actionability": 0.9,
        },
    )

    result = runtime.process(knowledge)

    assert result.runtime_id.startswith("AI5R-KRT-")
    assert result.knowledge_object.classification["domain"] == "business"
    assert result.knowledge_object.priority["priority_level"] in ["HIGH", "CRITICAL"]
    assert "classification" in result.stages
    assert "prioritization" in result.stages


def test_knowledge_runtime_accepts_dict():
    runtime = KnowledgeRuntime()

    result = runtime.process({
        "knowledge_id": "KO-R002",
        "summary": "Build python module and unit test for API workflow",
        "impact": 0.8,
        "urgency": 0.8,
        "actionability": 0.9,
    })

    assert result.knowledge_object.knowledge_id == "KO-R002"
    assert result.knowledge_object.classification["domain"] == "technical"


def test_knowledge_runtime_emits_event():
    runtime = KnowledgeRuntime()

    result = runtime.process({
        "knowledge_id": "KO-R003",
        "summary": "School curriculum needs assessment plan",
    })

    event = result.events[0]

    assert event.event_type == "KNOWLEDGE_PROCESSED"
    assert event.source_object_id == "KO-R003"
    assert event.source_object_type == "KNOWLEDGE_OBJECT"
    assert event.payload["runtime_id"] == runtime.runtime_id
    assert event.payload["knowledge_id"] == "KO-R003"


def test_knowledge_runtime_stores_events():
    runtime = KnowledgeRuntime()

    runtime.process({
        "knowledge_id": "KO-R004",
        "summary": "Factory pipeline requires registry integration",
    })

    assert len(runtime.emitted_events()) == 1
    assert runtime.emitted_events()[0].event_type == "KNOWLEDGE_PROCESSED"


def test_knowledge_runtime_process_many():
    runtime = KnowledgeRuntime()

    results = runtime.process_many([
        {
            "knowledge_id": "KO-R005",
            "summary": "UMKM customer market revenue strategy",
        },
        {
            "knowledge_id": "KO-R006",
            "summary": "Teacher assessment and curriculum plan",
        },
    ])

    assert len(results) == 2
    assert results[0].knowledge_object.classification["domain"] == "business"
    assert results[1].knowledge_object.classification["domain"] == "education"


def test_knowledge_runtime_rejects_empty_many():
    runtime = KnowledgeRuntime()

    try:
        runtime.process_many([])
        assert False
    except ValueError as error:
        assert "knowledge_objects are required" in str(error)
