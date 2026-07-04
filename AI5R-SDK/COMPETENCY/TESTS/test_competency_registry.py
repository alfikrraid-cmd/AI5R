import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_object import CompetencyObject
from COMPETENCY.competency_registry import CompetencyRegistry


def test_competency_registry():
    registry = CompetencyRegistry()

    competency = CompetencyObject(
        organization_id="ORG-001",
        capability_id="CAP-001",
        competency_code="CM-003",
        competency_name="Pump Inspection Competency",
        success_rate=0.98,
        accuracy_score=0.96,
        failure_rate=0.02,
        evidence_count=10,
    )

    registered = registry.register(competency)

    assert registered == competency
    assert registry.exists(competency.competency_id) is True
    assert registry.get(competency.competency_id) == competency
    assert len(registry.list_all()) == 1
    assert registry.list_by_organization("ORG-001") == [competency]
    assert registry.list_by_capability("CAP-001") == [competency]
    assert registry.list_by_status("ACTIVE") == [competency]

    print("CM-003 Competency Registry OK")


if __name__ == "__main__":
    test_competency_registry()
