import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_manifest import KnowledgeManifest


def test_knowledge_manifest():
    manifest = KnowledgeManifest()

    data = manifest.to_dict()

    assert data["subsystem"] == "KNOWLEDGE"
    assert data["foundation_version"] == "1.0"
    assert data["runtime"] == "KnowledgeRuntime"
    assert data["registry"] == "KnowledgeRegistry"

    assert "KnowledgeIngestionEngine" in data["engines"]
    assert "KnowledgeValidationEngine" in data["engines"]
    assert "KnowledgeChunkingEngine" in data["engines"]
    assert "KnowledgeRetrievalEngine" in data["engines"]

    assert "KnowledgeObject" in data["objects"]
    assert "KnowledgeSource" in data["objects"]
    assert "KnowledgeChunk" in data["objects"]

    assert data["status"] == "FROZEN_CANDIDATE"

    print("KF-003 Knowledge Manifest OK")


if __name__ == "__main__":
    test_knowledge_manifest()
