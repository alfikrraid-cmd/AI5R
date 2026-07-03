import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject
from KNOWLEDGE.knowledge_chunking_engine import KnowledgeChunkingEngine
from KNOWLEDGE.knowledge_retrieval_engine import KnowledgeRetrievalEngine


def test_knowledge_retrieval_engine():
    knowledge = KnowledgeObject(
        organization_id="ORG-001",
        knowledge_code="KNW-PUMP-001",
        title="Pump Maintenance Knowledge",
        content=(
            "Pump vibration inspection is required. "
            "Bearing temperature must be checked. "
            "Seal condition must be monitored. "
            "Lubrication schedule is mandatory."
        ),
        source_type="MANUAL",
    )

    chunks = KnowledgeChunkingEngine().chunk(
        knowledge,
        max_chars=50,
    )

    engine = KnowledgeRetrievalEngine()

    results = engine.search(
        chunks=chunks,
        organization_id="ORG-001",
        query="bearing temperature",
        limit=3,
    )

    assert len(results) >= 1
    assert results[0]["score"] >= 1
    assert results[0]["chunk"].organization_id == "ORG-001"

    no_cross_org = engine.search(
        chunks=chunks,
        organization_id="ORG-999",
        query="bearing",
    )

    assert len(no_cross_org) == 0

    print("KF-005 Knowledge Retrieval Engine OK")


if __name__ == "__main__":
    test_knowledge_retrieval_engine()
