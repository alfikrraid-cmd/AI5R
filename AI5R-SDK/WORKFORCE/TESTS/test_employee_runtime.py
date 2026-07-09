from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory
from WORKFORCE.employee_runtime import EmployeeRuntime
from WORKFORCE.work_item import WorkItem


def _employee():
    return DigitalEmployeeFactory().manufacture(
        employee_name="AI Backend",
        organization_id="ORG-AI5R",
        identity_id="ID-001",
        position_id="BACKEND_ENGINEER",
        kernel_id="KERNEL-AI5R",
    )["employee"]


def test_employee_runtime_lifecycle():

    employee = _employee()

    work = WorkItem(
        title="Build Login API",
        assigned_position_id="BACKEND_ENGINEER",
    )

    runtime = EmployeeRuntime()

    assert runtime.receive_work(employee, work).phase == "THINKING"
    assert runtime.think(employee, work).phase == "EXECUTING"
    assert runtime.execute(employee, work).phase == "REVIEWING"
    assert runtime.review(employee, work).phase == "LEARNING"

    result = runtime.learn(employee, work)

    assert result.status == "COMPLETED"
    assert result.phase == "IDLE"
    assert employee.metadata["runtime_state"] == "IDLE"
