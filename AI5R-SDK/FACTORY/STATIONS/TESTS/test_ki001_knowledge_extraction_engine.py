from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.STATIONS.knowledge_manufacturing_station import (
    KnowledgeManufacturingInput,
    KnowledgeManufacturingStation,
)


def build_memory_object(observation):
    return {
        "type": "MEMORY_OBJECT",
        "memory_id": "MEM-001",
        "experience_object": {
            "type": "EXPERIENCE_OBJECT",
            "warehouse_object": {
                "type": "WAREHOUSE_OBJECT",
                "reality_object": {
                    "type": "REALITY_OBJECT",
                    "payload": {
                        "observation": observation
                    },
                },
            },
        },
    }


def test_extracts_ltsa_service_agreement_need():
    result = KnowledgeManufacturingStation().manufacture(
        KnowledgeManufacturingInput(
            memory_object=build_memory_object(
                "customer needs LTSA technical service agreement support"
            )
        )
    )

    knowledge = result.knowledge_object["extracted_knowledge"]

    assert knowledge["knowledge_type"] == "SERVICE_AGREEMENT_NEED"
    assert knowledge["confidence"] == 0.9
    assert "Technical Service Agreement" in knowledge["pattern"]


def test_extracts_pump_failure_pattern():
    result = KnowledgeManufacturingStation().manufacture(
        KnowledgeManufacturingInput(
            memory_object=build_memory_object(
                "customer reports pump failure after maintenance"
            )
        )
    )

    knowledge = result.knowledge_object["extracted_knowledge"]

    assert knowledge["knowledge_type"] == "FAILURE_PATTERN"
    assert knowledge["confidence"] == 0.85
    assert knowledge["pattern"] == "Pump Failure Pattern"


def test_extracts_general_observation():
    result = KnowledgeManufacturingStation().manufacture(
        KnowledgeManufacturingInput(
            memory_object=build_memory_object(
                "customer asks for general product information"
            )
        )
    )

    knowledge = result.knowledge_object["extracted_knowledge"]

    assert knowledge["knowledge_type"] == "GENERAL_OBSERVATION"
    assert knowledge["confidence"] == 0.5
