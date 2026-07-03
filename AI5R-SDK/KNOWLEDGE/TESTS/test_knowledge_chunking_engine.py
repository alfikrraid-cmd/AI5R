import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject
from KNOWLEDGE.knowledge_chunking_engine import KnowledgeChunkingEngine


def test_knowledge_chunking_engine():
    knowledge = KnowledgeObject(
        organization_id="ORG-001",
        knowledge_code="KNW-PUMP-001",
        title="Pump Maintenance Knowledge",
        content=(
            "Pump maintenance requires vibration inspection. "
            "Bearing temperature must be checked regularly. "
            "Seal condition must be monitored. "
            "Lubrication schedule must be followed."
        ),
        source_type="MANUAL",
        metadata={"domain": "power_plant"},
    )

    engine = KnowledgeChunkingEngine()
    chunks = engine.chunk(knowledge, max_chars=60)

    assert len(chunks) >= 2
    assert chunks[0].knowledge_id == knowledge.knowledge_id
    assert chunks[0].organization_id == "ORG-001"
    assert chunks[0].chunk_index == 0
    assert chunks[0].metadata["knowledge_code"] == "KNW-PUMP-001"
    assert "Pump maintenance" in chunks[0].content

    print("KF-004 Knowledge Chunking Engine OK")


if __name__ == "__main__":
    test_knowledge_chunking_engine()
