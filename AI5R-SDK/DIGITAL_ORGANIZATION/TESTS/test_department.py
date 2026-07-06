import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import (
    DigitalEmployee,
    EmployeeIdentity,
    EmployeeCapability,
)

from DIGITAL_ORGANIZATION import Department


def create_employee(name):

    identity = EmployeeIdentity(
        name=name,
        organization="AI5R",
        department="Marketing",
        position="Marketing Executive",
    )

    capability = EmployeeCapability(
        capabilities=["Marketing"]
    )

    employee = DigitalEmployee(identity, capability)

    employee.initialize()
    employee.ready()

    return employee


def test_department_runtime():

    department = Department("Marketing")

    department.add_employee(create_employee("Alice"))
    department.add_employee(create_employee("Bob"))
    department.add_employee(create_employee("Charlie"))

    assert department.employee_count() == 3

    result = department.assign_task("Create Campaign")

    assert len(result) == 3

    assert result[0]["status"] == "EXECUTED"
