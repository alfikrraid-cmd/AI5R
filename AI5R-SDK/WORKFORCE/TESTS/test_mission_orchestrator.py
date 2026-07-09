from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.mission_orchestrator import MissionOrchestrator
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_event_bus import WorkforceEventBus


def test_mission_orchestrator_runs_employee_lifecycle():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-012",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API", "TESTING"],
    )["employee"]

    work_item = WorkItem(
        title="Build FastAPI Login API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    result = MissionOrchestrator(activity_registry=registry).run(
        employee=employee,
        work_item=work_item,
        mission_id="MISSION-DEMO-001",
    )

    assert result.mission_id == "MISSION-DEMO-001"
    assert result.status == "COMPLETED"
    assert result.activity_count == 5
    assert result.runtime_phases == [
        "RECEIVED",
        "EXECUTING",
        "REVIEWING",
        "LEARNING",
        "IDLE",
    ]
    assert len(registry.snapshot()) == 5
    assert len(bus.stream()) == 5
    assert registry.snapshot()[-1]["status"] == "COMPLETED"


def test_mission_orchestrator_result_is_dashboard_ready():
    registry = EmployeeActivityRegistry()

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI QA Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-QA-012",
        position_id="QA_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["TESTING"],
    )["employee"]

    work_item = WorkItem(
        title="Review API contract",
        assigned_position_id="QA_ENGINEER",
    )

    result = MissionOrchestrator(activity_registry=registry).run(
        employee=employee,
        work_item=work_item,
    )

    assert result.mission_id.startswith("MISSION-")
    assert result.metadata["work_item_title"] == "Review API contract"
    assert result.metadata["employee_name"] == "AI QA Engineer"
    assert result.metadata["position_id"] == "QA_ENGINEER"
