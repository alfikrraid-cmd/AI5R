from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE.CONTEXT import EmployeeContext, EmployeeContextManager


def test_employee_context_snapshot():
    context = EmployeeContext(
        employee_id="EMP-001",
        role="Marketing Manager",
        department_id="DPT-001",
        organization_id="ORG-001",
        active_goal="Increase qualified leads",
        metadata={"channel": "instagram"},
    )

    snapshot = context.snapshot()

    assert snapshot["employee_id"] == "EMP-001"
    assert snapshot["role"] == "Marketing Manager"
    assert snapshot["department_id"] == "DPT-001"
    assert snapshot["organization_id"] == "ORG-001"
    assert snapshot["active_goal"] == "Increase qualified leads"
    assert snapshot["metadata"]["channel"] == "instagram"
    assert snapshot["created_at"]
    assert snapshot["updated_at"]


def test_employee_context_update():
    context = EmployeeContext(employee_id="EMP-002")

    context.update(
        role="Sales Agent",
        department_id="DPT-002",
        active_goal="Close inbound leads",
    )

    assert context.role == "Sales Agent"
    assert context.department_id == "DPT-002"
    assert context.active_goal == "Close inbound leads"


def test_employee_context_rejects_unknown_field():
    context = EmployeeContext(employee_id="EMP-003")

    try:
        context.update(unknown_field=True)
    except AttributeError as exc:
        assert "Unknown employee context field" in str(exc)
    else:
        raise AssertionError("Expected AttributeError")


def test_employee_context_metadata():
    context = EmployeeContext(employee_id="EMP-004")

    context.attach_metadata("priority", "HIGH")

    assert context.metadata["priority"] == "HIGH"


def test_employee_context_manager_create_and_get():
    manager = EmployeeContextManager()

    context = manager.create_context(
        employee_id="EMP-005",
        role="Operator",
        department_id="DPT-OPS",
        organization_id="ORG-AI5R",
        active_goal="Run workflow",
        metadata={"shift": "morning"},
    )

    assert manager.get_context("EMP-005") is context
    assert context.role == "Operator"
    assert context.metadata["shift"] == "morning"


def test_employee_context_manager_update():
    manager = EmployeeContextManager()
    manager.create_context(employee_id="EMP-006")

    context = manager.update_context(
        "EMP-006",
        role="Supervisor",
        active_goal="Review output",
    )

    assert context.role == "Supervisor"
    assert context.active_goal == "Review output"


def test_employee_context_manager_attach_metadata():
    manager = EmployeeContextManager()
    manager.create_context(employee_id="EMP-007")

    context = manager.attach_metadata("EMP-007", "source", "runtime")

    assert context.metadata["source"] == "runtime"


def test_employee_context_manager_snapshot():
    manager = EmployeeContextManager()
    manager.create_context(employee_id="EMP-008", role="Analyst")

    snapshot = manager.snapshot()

    assert snapshot["EMP-008"]["role"] == "Analyst"


def test_employee_context_manager_requires_existing_context():
    manager = EmployeeContextManager()

    try:
        manager.require_context("EMP-MISSING")
    except KeyError as exc:
        assert "Employee context not found" in str(exc)
    else:
        raise AssertionError("Expected KeyError")
