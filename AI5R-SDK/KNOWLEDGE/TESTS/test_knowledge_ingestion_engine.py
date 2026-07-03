import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_source import KnowledgeSource
from KNOWLEDGE.knowledge_ingestion_engine import KnowledgeIngestionEngine


def test_knowledge_ingestion_engine():
    source = KnowledgeSource(
        organization_id="ORG-001",
        department_id="DEPT-KNOWLEDGE-001",
        source_code="SRC-MANUAL-001",
        source_name="Pump Maintenance Manual",
        source_type="PDF_MANUAL",
        source_uri="manuals/pump-maintenance.pdf",
        metadata={
            "domain": "power_plant",
            "trust_level": "high",
        },
    )

    engine = KnowledgeIngestionEngine()

    knowledge = engine.ingest(
        source=source,
        title="Pump Maintenance Procedure",
        content="Inspect vibration, seal condition, bearing temperature, and lubrication schedule.",
        metadata={
            "language": "en",
            "section": "maintenance",
        },
    )

    assert knowledge.organization_id == source.organization_id
    assert knowledge.department_id == source.department_id
    assert knowledge.knowledge_code == "KNW-SRC-MANUAL-001"
    assert knowledge.source_type == "PDF_MANUAL"
    assert knowledge.metadata["source_id"] == source.source_id
    assert knowledge.metadata["trust_level"] == "high"
    assert knowledge.metadata["language"] == "en"
    assert "bearing temperature" in knowledge.content

    print("KF-003 Knowledge Ingestion Engine OK")


if __name__ == "__main__":
    test_knowledge_ingestion_engine()
