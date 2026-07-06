import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_EMPLOYEE import (
    DigitalEmployee,
    EmployeeIdentity,
    EmployeeCapability,
)


def test_employee_runtime():

    identity = EmployeeIdentity(
        name="Marketing AI",
        organization="AI5R",
        department="Marketing",
        position="Marketing Manager",
    )

    capability = EmployeeCapability(
        capabilities=["SEO", "Branding"]
    )

    employee = DigitalEmployee(identity, capability)

    employee.initialize()
    employee.ready()

    employee.assign("Create Campaign")

    result = employee.execute()

    assert result["status"] == "EXECUTED"

    employee.evaluate()

    employee.learn()

    assert employee.identity.position == "Marketing Manager"
