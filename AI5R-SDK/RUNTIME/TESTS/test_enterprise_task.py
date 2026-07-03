import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_task import EnterpriseTask


def test_enterprise_task_object():
    task = EnterpriseTask(
        task_type="extract_pump_findings",
        title="Extract Pump Findings",
        instruction="Extract defects, observations, and operating signals from uploaded pump report",
        mission_id="mission-001",
        input_object={"warehouse_object_id": "warehouse-report-001"},
    )

    obj = task.to_enterprise_object()

    assert obj["object_type"] == "enterprise_task"
    assert obj["task_type"] == "extract_pump_findings"
    assert obj["mission_id"] == "mission-001"
    assert obj["status"] == "created"
    assert obj["input_object"]["warehouse_object_id"] == "warehouse-report-001"


def test_enterprise_task_assignment():
    task = EnterpriseTask(
        task_type="extract_pump_findings",
        title="Extract Pump Findings",
        instruction="Extract findings",
        mission_id="mission-001",
    )

    task.assign("worker-knowledge-engine")

    assert task.assigned_worker == "worker-knowledge-engine"
    assert task.status == "assigned"


def test_enterprise_task_lifecycle():
    task = EnterpriseTask(
        task_type="generate_recommendation",
        title="Generate Recommendation",
        instruction="Generate maintenance recommendation",
        mission_id="mission-001",
    )

    task.start()
    assert task.status == "running"

    task.complete({
        "recommendation": "Inspect bearing alignment and lubrication condition"
    })

    assert task.status == "completed"
    assert "recommendation" in task.output_object


if __name__ == "__main__":
    test_enterprise_task_object()
    test_enterprise_task_assignment()
    test_enterprise_task_lifecycle()
    print("EP-002 Enterprise Task OK")
