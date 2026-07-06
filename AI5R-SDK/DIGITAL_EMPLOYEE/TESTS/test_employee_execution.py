import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import DigitalEmployee, EmployeeExecutionEngine, EmployeeTask, ExecutionResult


def test_employee_execution_engine():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Marketing AI",
        department="Marketing",
        role="Manager",
        identity_id="ID-001",
    )

    employee.add_capability("Branding")

    task = EmployeeTask(
        title="Create Campaign",
        description="Create brand campaign",
        priority="HIGH",
    )

    engine = EmployeeExecutionEngine()
    result = engine.execute(employee, task)

    assert isinstance(result, ExecutionResult)
    assert result.employee_id == "EMP-001"
    assert result.task_title == "Create Campaign"
    assert result.status == "EXECUTED"
    assert "Branding" in result.output["capabilities_used"]
