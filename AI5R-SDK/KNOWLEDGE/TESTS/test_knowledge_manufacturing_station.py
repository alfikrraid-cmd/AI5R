import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_manufacturing_station import (
    KnowledgeManufacturingStation,
)


def test_knowledge_manufacturing_station():
    station = KnowledgeManufacturingStation()

    result = station.run()

    assert result["station"] == "knowledge"
    assert result["status"] == "SUCCESS"

    manifest = result["manifest"]

    assert manifest["subsystem"] == "KNOWLEDGE"
    assert manifest["runtime"] == "KnowledgeRuntime"
    assert manifest["registry"] == "KnowledgeRegistry"

    print("KF-004 Knowledge Manufacturing Station OK")


if __name__ == "__main__":
    test_knowledge_manufacturing_station()
