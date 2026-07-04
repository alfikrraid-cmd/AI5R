import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_runtime import KnowledgeRuntime
from KNOWLEDGE.knowledge_source import KnowledgeSource


def test_knowledge_runtime():
    runtime = KnowledgeRuntime()

    source = KnowledgeSource(
        organization_id="org-001",
        department_id="dept-001",
        source_code="SRC-001",
        source_type="manual",
        metadata={"trust_level": "verified"},
    )

    result = runtime.process(
        source=source,
        title="Pump Maintenance Procedure",
        content=(
            "Pump maintenance requires inspection of seals, bearings, "
            "alignment, lubrication, vibration, and operational history."
        ),
        metadata={"domain": "maintenance"},
        max_chars=40,
    )

    assert result["status"] == "PROCESSED"
    assert result["validation"]["valid"] is True
    assert result["knowledge"].knowledge_id is not None
    assert len(result["chunks"]) > 1

    knowledge_id = result["knowledge"].knowledge_id

    assert runtime.get(knowledge_id) == result["knowledge"]
    assert len(runtime.list_all()) == 1
    assert len(runtime.list_chunks()) > 1

    search_results = runtime.search(
        organization_id="org-001",
        query="pump seals",
    )

    assert len(search_results) >= 1
    assert search_results[0]["score"] >= 1

    print("KF-002 Knowledge Runtime OK")


if __name__ == "__main__":
    test_knowledge_runtime()
