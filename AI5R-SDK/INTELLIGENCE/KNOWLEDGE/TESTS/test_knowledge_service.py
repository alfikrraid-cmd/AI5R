import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.KNOWLEDGE.knowledge_service import KnowledgeService


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_service_processes_dict():
    service = KnowledgeService()

    result = service.process(
        {
            "knowledge_id": "KO-S001",
            "summary": "UMKM pricing strategy increases revenue",
            "impact": 0.9,
            "urgency": 0.8,
            "actionability": 0.9,
        }
    )

    assert result.knowledge_object.classification["domain"] == "business"
    assert result.runtime_result.pipeline_id.startswith("AI5R-PIPE-")


def test_service_processes_object():
    service = KnowledgeService()

    knowledge = KnowledgeObject(
        knowledge_id="KO-S002",
        summary="Build python API workflow module",
    )

    result = service.process(knowledge)

    assert result.knowledge_object.object_type == "KNOWLEDGE_OBJECT"
    assert result.knowledge_object.classification["domain"] == "technical"


def test_runtime_generates_event():
    service = KnowledgeService()

    result = service.process(
        {
            "knowledge_id": "KO-S003",
            "summary": "School curriculum assessment",
        }
    )

    assert len(result.runtime_result.events) == 1
    assert result.runtime_result.events[0].event_type == "RUNTIME_EXECUTED"
