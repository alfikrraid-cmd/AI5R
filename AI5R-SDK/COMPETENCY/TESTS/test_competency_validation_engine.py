import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_object import CompetencyObject
from COMPETENCY.competency_validation_engine import CompetencyValidationEngine


def test_competency_validation_engine():
    competency = CompetencyObject(
        organization_id="ORG-001",
        capability_id="CAP-001",
        competency_code="CM-004",
        competency_name="Pump Inspection Competency",
        success_rate=0.98,
        accuracy_score=0.96,
        failure_rate=0.02,
        evidence_count=10,
        evidence_ids=["EX-001"],
    )

    validator = CompetencyValidationEngine()
    result = validator.validate(competency)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["competency_code"] == "CM-004"
    assert result["capability_id"] == "CAP-001"

    print("CM-004 Competency Validation Engine OK")


if __name__ == "__main__":
    test_competency_validation_engine()
