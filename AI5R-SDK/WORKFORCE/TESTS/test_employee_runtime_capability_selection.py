from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.work_item import WorkItem


def test_employee_runtime_selects_matching_capability():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["API", "JWT", "DATABASE"],
    )["employee"]

    work = WorkItem(
        title="Build JWT Login API",
        assigned_position_id="BACKEND_ENGINEER",
        description="Create authentication endpoint",
    )

    runtime = EmployeeRuntime()

    runtime.receive_work(employee, work)
    result = runtime.think(employee, work)

    assert result.phase == "EXECUTING"
    assert "API" in result.metadata["selected_capabilities"]
    assert "JWT" in result.metadata["selected_capabilities"]
    assert employee.metadata["selected_capabilities"] == ["API", "JWT"]


def test_employee_runtime_returns_empty_capability_when_no_match():
    employee = DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend",
        organization_id="ORG-AI5R",
        identity_id="ID-BACKEND-002",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
        capability_ids=["DATABASE"],
    )["employee"]

    work = WorkItem(
        title="Write API documentation",
        assigned_position_id="DOCUMENTATION_ENGINEER",
    )

    runtime = EmployeeRuntime()

    runtime.receive_work(employee, work)
    result = runtime.think(employee, work)

    assert result.metadata["selected_capabilities"] == []
    assert employee.metadata["selected_capabilities"] == []
