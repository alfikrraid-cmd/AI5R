import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_source import KnowledgeSource
from KNOWLEDGE.knowledge_pipeline import KnowledgePipeline


def test_knowledge_pipeline():
    source = KnowledgeSource(
        organization_id="ORG-001",
        department_id="DEPT-KNOWLEDGE-001",
        source_code="SRC-PUMP-001",
        source_name="Pump Maintenance Manual",
        source_type="PDF_MANUAL",
        source_uri="manuals/pump.pdf",
        metadata={
            "trust_level": "high",
            "domain": "power_plant",
        },
    )

    pipeline = KnowledgePipeline()

    result = pipeline.run(
        source=source,
        title="Pump Maintenance Procedure",
        content=(
            "Pump maintenance requires vibration inspection, bearing temperature checks, "
            "seal condition monitoring, and lubrication schedule compliance."
        ),
        metadata={
            "language": "en",
            "section": "maintenance",
        },
        max_chars=60,
    )

    assert result["success"] is True
    assert result["validation"]["valid"] is True
    assert result["knowledge"].knowledge_code == "KNW-SRC-PUMP-001"
    assert len(result["chunks"]) >= 2
    assert len(pipeline.registry.list_by_organization("ORG-001")) == 1

    print("KF-007 Knowledge Pipeline OK")


if __name__ == "__main__":
    test_knowledge_pipeline()
