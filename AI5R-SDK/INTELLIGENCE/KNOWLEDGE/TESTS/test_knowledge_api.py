import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FOUNDATION.canonical_identity import CanonicalIdentityGenerator
from INTELLIGENCE.KNOWLEDGE.API.knowledge_api import KnowledgeAPI
from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject


def setup_function():
    CanonicalIdentityGenerator.reset()


def test_knowledge_api_processes_payload():
    api = KnowledgeAPI()

    response = api.process({
        "knowledge_id": "KO-A001",
        "summary": "UMKM pricing strategy increases revenue",
        "impact": 0.9,
        "urgency": 0.8,
        "actionability": 0.9,
    })

    assert response.status == "processed"
    assert response.knowledge_id == "KO-A001"
    assert response.data["knowledge"]["classification"]["domain"] == "business"
    assert response.data["knowledge"]["priority"]["priority_level"] in ["HIGH", "CRITICAL"]


def test_knowledge_api_returns_event_data():
    api = KnowledgeAPI()

    response = api.process({
        "knowledge_id": "KO-A002",
        "summary": "Build python module and unit test for workflow",
    })

    events = response.data["events"]

    assert len(events) == 1
    assert events[0]["event_type"] == "KNOWLEDGE_PROCESSED"
    assert events[0]["source_object_id"] == "KO-A002"


def test_knowledge_api_process_many():
    api = KnowledgeAPI()

    responses = api.process_many([
        {
            "knowledge_id": "KO-A003",
            "summary": "School curriculum needs assessment plan",
        },
        {
            "knowledge_id": "KO-A004",
            "summary": "Factory pipeline requires registry integration",
        },
    ])

    assert len(responses) == 2
    assert responses[0].data["knowledge"]["classification"]["domain"] == "education"
    assert responses[1].data["knowledge"]["classification"]["domain"] == "operation"


def test_knowledge_api_create_object():
    api = KnowledgeAPI()

    obj = api.create_object({
        "knowledge_id": "KO-A005",
        "summary": "Customer market research supports revenue strategy",
    })

    assert isinstance(obj, KnowledgeObject)
    assert obj.knowledge_id == "KO-A005"


def test_knowledge_api_rejects_empty_payload():
    api = KnowledgeAPI()

    try:
        api.process({})
        assert False
    except ValueError as error:
        assert "payload is required" in str(error)
