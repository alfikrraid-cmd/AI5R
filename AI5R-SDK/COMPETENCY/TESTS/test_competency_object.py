import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_object import CompetencyObject


def test_competency_object():
    competency = CompetencyObject(
        organization_id="ORG-001",
        capability_id="CAP-001",
        competency_code="CM-001",
        competency_name="Pump Inspection Competency",
        success_rate=0.98,
        accuracy_score=0.96,
        failure_rate=0.02,
        evidence_count=100,
        evidence_ids=["EV-001"],
    )

    assert competency.object_type == "COMPETENCY"
    assert competency.capability_id == "CAP-001"
    assert competency.success_rate == 0.98
    assert competency.accuracy_score == 0.96
    assert competency.evidence_count == 100

    print("CM-001 Competency Object OK")


if __name__ == "__main__":
    test_competency_object()
