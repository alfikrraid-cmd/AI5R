from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_activity_registry import EmployeeActivityRegistry
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.work_item import WorkItem
from WORKFORCE.workforce_event_bus import WorkforceEventBus


def test_employee_runtime_records_activity_events():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API"],
    )["employee"]

    work_item = WorkItem(
        title="Build API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    runtime = EmployeeRuntime(activity_registry=registry)

    runtime.receive_work(employee, work_item)
    runtime.think(employee, work_item)
    runtime.execute(employee, work_item)
    runtime.review(employee, work_item)
    runtime.learn(employee, work_item)

    snapshot = registry.snapshot()
    stream = bus.stream()

    assert len(snapshot) == 5
    assert len(stream) == 5
    assert snapshot[0]["activity_type"] == "RECEIVED_WORK"
    assert snapshot[-1]["status"] == "COMPLETED"
    assert snapshot[-1]["progress"] == 100


def test_employee_runtime_activity_snapshot_is_dashboard_ready():
    bus = WorkforceEventBus()
    registry = EmployeeActivityRegistry(event_bus=bus)

    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend Engineer",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-002",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API"],
    )["employee"]

    work_item = WorkItem(
        title="Build API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    runtime = EmployeeRuntime(activity_registry=registry)
    runtime.receive_work(employee, work_item)

    snapshot = registry.snapshot()[0]

    assert snapshot["employee_id"] == employee.employee_id
    assert snapshot["work_item_id"] == work_item.work_item_id
    assert snapshot["status"] == "THINKING"
    assert snapshot["message"] == "Employee received work item"
