import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from COMPETENCY.competency_runtime import CompetencyRuntime


def test_competency_runtime():
    runtime = CompetencyRuntime()

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

    result = runtime.measure_and_register(
        organization_id="ORG-001",
        capability_id="CAP-001",
        competency_code="CM-005",
        competency_name="Pump Inspection Competency",
        executions=executions,
        metadata={"source": "unit-test"},
    )

    assert result["status"] == "REGISTERED"
    assert result["validation"]["valid"] is True

    competency = result["competency"]

    assert runtime.get(competency.competency_id) == competency
    assert runtime.list_by_organization("ORG-001") == [competency]
    assert runtime.list_by_capability("CAP-001") == [competency]
    assert runtime.list_by_status("ACTIVE") == [competency]

    print("CM-005 Competency Runtime OK")


if __name__ == "__main__":
    test_competency_runtime()
