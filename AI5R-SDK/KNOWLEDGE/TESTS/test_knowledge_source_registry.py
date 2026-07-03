import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_source import KnowledgeSource
from KNOWLEDGE.knowledge_source_registry import KnowledgeSourceRegistry


def test_knowledge_source_registry():
    registry = KnowledgeSourceRegistry()

    source = KnowledgeSource(
        organization_id="ORG-001",
        department_id="DEPT-KNOWLEDGE-001",
        source_code="SRC-YT-001",
        source_name="Pump Maintenance YouTube Transcript",
        source_type="YOUTUBE_TRANSCRIPT",
        source_uri="https://youtube.com/example",
        metadata={
            "language": "en",
            "domain": "power_plant",
            "trust_level": "medium",
        },
    )

    registry.register(source)

    assert registry.get(source.source_id).source_code == "SRC-YT-001"
    assert len(registry.list_by_organization("ORG-001")) == 1
    assert len(registry.list_by_department("DEPT-KNOWLEDGE-001")) == 1
    assert registry.find_by_type("YOUTUBE_TRANSCRIPT")[0].source_name == "Pump Maintenance YouTube Transcript"

    print("KF-002 Knowledge Source Registry OK")


if __name__ == "__main__":
    test_knowledge_source_registry()
