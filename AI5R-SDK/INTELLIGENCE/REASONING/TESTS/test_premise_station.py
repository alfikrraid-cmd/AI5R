import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from INTELLIGENCE.KNOWLEDGE.knowledge_object import KnowledgeObject
from INTELLIGENCE.REASONING.CONTRACTS.reasoning_contract import (
    ReasoningStationInput,
)
from INTELLIGENCE.REASONING.reasoning_object import ReasoningObject
from INTELLIGENCE.REASONING.STATIONS.premise_station import (
    PremiseManufacturingStation,
)


def test_premise_station_creates_premises_from_knowledge_objects():
    station = PremiseManufacturingStation()
    reasoning = ReasoningObject()

    knowledge = KnowledgeObject(
        knowledge_id="KO-RS001",
        summary="UMKM pricing strategy increases revenue",
    )
    knowledge.attach_classification({
        "domain": "business",
        "confidence": 0.9,
    })
    knowledge.attach_priority({
        "priority_level": "HIGH",
    })

    output = station.process(
        ReasoningStationInput(
            reasoning_object=reasoning,
            context={
                "knowledge_objects": [knowledge],
            },
        )
    )

    assert output.status == "processed"
    assert output.station_code == "RS-001"
    assert len(output.reasoning_object.premises) == 1
    assert output.reasoning_object.premises[0]["knowledge_id"] == "KO-RS001"
    assert output.reasoning_object.premises[0]["confidence"] == 0.9
    assert output.metadata["premise_count"] == 1


def test_premise_station_accepts_dict_knowledge():
    station = PremiseManufacturingStation()
    reasoning = ReasoningObject()

    output = station.process(
        ReasoningStationInput(
            reasoning_object=reasoning,
            context={
                "knowledge_objects": [
                    {
                        "knowledge_id": "KO-RS002",
                        "summary": "Customer demand supports sales growth",
                        "classification": {
                            "domain": "business",
                            "confidence": 0.8,
                        },
                    }
                ],
            },
        )
    )

    premise = output.reasoning_object.premises[0]

    assert premise["knowledge_id"] == "KO-RS002"
    assert premise["statement"] == "Customer demand supports sales growth"
    assert premise["classification"]["domain"] == "business"


def test_premise_station_adds_reasoning_trace():
    station = PremiseManufacturingStation()
    reasoning = ReasoningObject()

    station.process(
        ReasoningStationInput(
            reasoning_object=reasoning,
            context={
                "knowledge_objects": [
                    {
                        "knowledge_id": "KO-RS003",
                        "summary": "Factory registry improves integration",
                    }
                ],
            },
        )
    )

    assert "premises manufactured from knowledge objects" in reasoning.reasoning_path
    assert "KO-RS003" in reasoning.supporting_knowledge


def test_premise_station_rejects_missing_knowledge_objects:
    station = PremiseManufacturingStation()
    reasoning = ReasoningObject()

    try:
        station.process(
            ReasoningStationInput(
                reasoning_object=reasoning,
                context={},
            )
        )
        assert False
    except ValueError as error:
        assert "knowledge_objects are required" in str(error)
