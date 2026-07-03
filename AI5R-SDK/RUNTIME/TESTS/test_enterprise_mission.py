import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_mission import EnterpriseMission


def test_enterprise_mission_object():
    mission = EnterpriseMission(
        mission_type="ltsa_pump_report_analysis",
        title="Analyze Pump Report",
        objective="Convert uploaded pump report into recommendation and work order",
        source_object_id="warehouse-report-001",
        customer_id="customer-001",
    )

    obj = mission.to_enterprise_object()

    assert obj["object_type"] == "enterprise_mission"
    assert obj["mission_type"] == "ltsa_pump_report_analysis"
    assert obj["status"] == "created"
    assert obj["source_object_id"] == "warehouse-report-001"
    assert obj["customer_id"] == "customer-001"


def test_enterprise_mission_lifecycle():
    mission = EnterpriseMission(
        mission_type="ltsa_pump_report_analysis",
        title="Analyze Pump Report",
        objective="Generate recommendation",
    )

    mission.start()
    assert mission.status == "running"

    mission.complete()
    assert mission.status == "completed"


def test_enterprise_mission_task_attachment():
    mission = EnterpriseMission(
        mission_type="ltsa_pump_report_analysis",
        title="Analyze Pump Report",
        objective="Generate recommendation",
    )

    mission.add_task({
        "task_type": "extract_pump_findings",
        "status": "created",
    })

    assert len(mission.tasks) == 1
    assert mission.tasks[0]["task_type"] == "extract_pump_findings"


if __name__ == "__main__":
    test_enterprise_mission_object()
    test_enterprise_mission_lifecycle()
    test_enterprise_mission_task_attachment()
    print("EP-001 Enterprise Mission OK")
