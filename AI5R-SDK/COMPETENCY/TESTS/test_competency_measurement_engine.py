import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_measurement_engine import (
    CompetencyMeasurementEngine,
)


def test_competency_measurement_engine():
    executions = [
        {
            "execution_id": "EX-001",
            "status": "SUCCESS",
            "accuracy": 0.95,
        },
        {
            "execution_id": "EX-002",
            "status": "SUCCESS",
            "accuracy": 0.97,
        },
        {
            "execution_id": "EX-003",
            "status": "FAILED",
            "accuracy": 0.50,
        },
    ]

    engine = CompetencyMeasurementEngine()

    competency = engine.measure(
        organization_id="ORG-001",
        capability_id="CAP-001",
        competency_code="CM-002",
        competency_name="Pump Inspection Competency",
        executions=executions,
        metadata={"source": "unit-test"},
    )

    assert competency.capability_id == "CAP-001"
    assert competency.evidence_count == 3
    assert round(competency.success_rate, 2) == 0.67
    assert round(competency.failure_rate, 2) == 0.33
    assert round(competency.accuracy_score, 2) == 0.81
    assert competency.evidence_ids == ["EX-001", "EX-002", "EX-003"]

    print("CM-002 Competency Measurement Engine OK")


if __name__ == "__main__":
    test_competency_measurement_engine()
