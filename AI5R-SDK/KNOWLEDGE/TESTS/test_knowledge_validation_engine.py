import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KNOWLEDGE.knowledge_object import KnowledgeObject
from KNOWLEDGE.knowledge_validation_engine import KnowledgeValidationEngine


def test_knowledge_validation_engine():
    engine = KnowledgeValidationEngine()

    valid_knowledge = KnowledgeObject(
        organization_id="ORG-001",
        knowledge_code="KNW-PUMP-001",
        title="Pump Maintenance Knowledge",
        content="Pump maintenance requires vibration, bearing, seal, and lubrication inspection.",
        source_type="MANUAL",
        metadata={
            "trust_level": "high",
            "domain": "power_plant",
        },
    )

    result = engine.validate(valid_knowledge)

    assert result["valid"] is True
    assert len(result["errors"]) == 0

    weak_knowledge = KnowledgeObject(
        organization_id="ORG-001",
        knowledge_code="KNW-PUMP-002",
        title="Short Note",
        content="Too short",
        source_type="NOTE",
        metadata={
            "trust_level": "unknown",
        },
    )

    weak_result = engine.validate(weak_knowledge)

    assert weak_result["valid"] is False
    assert "Invalid trust_level" in weak_result["errors"]
    assert "Knowledge content is very short" in weak_result["warnings"]

    print("KF-006 Knowledge Validation Engine OK")


if __name__ == "__main__":
    test_knowledge_validation_engine()
