import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import DigitalEmployee


def test_create_employee():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    assert employee.employee_id == "EMP-001"
    assert employee.status == "ACTIVE"
    assert employee.capabilities == []


def test_add_capability():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    employee.add_capability("CAP-001")

    assert "CAP-001" in employee.capabilities


def test_no_duplicate_capability():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    employee.add_capability("CAP-001")
    employee.add_capability("CAP-001")

    assert len(employee.capabilities) == 1


def test_remove_capability():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    employee.add_capability("CAP-001")
    employee.remove_capability("CAP-001")

    assert employee.capabilities == []


def test_suspend_employee():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    employee.suspend()

    assert employee.status == "SUSPENDED"


def test_activate_employee():
    employee = DigitalEmployee(
        employee_id="EMP-001",
        employee_name="Finance AI",
        department="Finance",
        role="Analyst",
        identity_id="ID-001",
    )

    employee.suspend()
    employee.activate()

    assert employee.status == "ACTIVE"
