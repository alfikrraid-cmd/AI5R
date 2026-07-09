from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.mission_orchestrator import MissionOrchestrator
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_event_bus import WorkforceEventBus


def test_mission_orchestrator_uses_execution_plan_and_scheduler():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-SCHEDULER",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API"],
    )["employee"]

    work_item = WorkItem(
        title="Build Login API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    result = MissionOrchestrator(activity_registry=registry).run(
        employee=employee,
        work_item=work_item,
        mission_id="MISSION-SCHEDULER-001",
    )

    plan = result.execution_plan

    assert result.status == "COMPLETED"
    assert plan["mission_id"] == "MISSION-SCHEDULER-001"
    assert plan["completed"] == [work_item.work_item_id]
    assert plan["running"] == []
    assert plan["waiting"] == []
    assert result.activity_count == 5
    assert len(bus.stream()) == 5


def test_mission_orchestrator_result_contains_execution_plan_snapshot():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI QA Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-QA-SCHEDULER",
        position_id="QA_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["TESTING"],
    )["employee"]

    work_item = WorkItem(
        title="Review Login API",
        assigned_position_id="QA_ENGINEER",
    )

    result = MissionOrchestrator().run(
        employee=employee,
        work_item=work_item,
    )

    assert result.execution_plan["plan_id"].startswith("WEP-")
    assert result.execution_plan["metadata"]["objective"] == "Review Login API"
