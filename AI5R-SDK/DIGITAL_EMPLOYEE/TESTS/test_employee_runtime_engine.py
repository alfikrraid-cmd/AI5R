import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import (
    EmployeeRuntimeEngine,
    EmployeeState,
)


def test_employee_lifecycle():
    employee = EmployeeRuntimeEngine(
        employee_id="EMP-001",
        employee_name="Marketing Manager",
    )

    assert employee.start() == EmployeeState.READY
    assert employee.observe() == EmployeeState.OBSERVING
    assert employee.think() == EmployeeState.PLANNING
    assert employee.decide() == EmployeeState.PLANNING
    assert employee.execute() == EmployeeState.WORKING
    assert employee.learn() == EmployeeState.LEARNING
    assert employee.wait() == EmployeeState.READY
    assert employee.stop() == EmployeeState.SUSPENDED


def test_goal_and_task():
    employee = EmployeeRuntimeEngine(
        employee_id="EMP-002",
        employee_name="Finance",
    )

    employee.assign_goal("Increase revenue")
    employee.assign_task("Prepare report")

    snapshot = employee.snapshot()

    assert snapshot["goal"] == "Increase revenue"
    assert snapshot["task"] == "Prepare report"


def test_history():
    employee = EmployeeRuntimeEngine(
        employee_id="EMP-003",
        employee_name="CEO",
    )

    employee.start()
    employee.observe()
    employee.think()
    employee.execute()

    assert employee.history == [
        "START",
        "OBSERVE",
        "THINK",
        "EXECUTE",
    ]
