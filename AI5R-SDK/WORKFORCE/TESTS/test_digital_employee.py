import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WORKFORCE.digital_employee import DigitalEmployee


def test_digital_employee():

    employee = DigitalEmployee(
        employee_name="CEO AI",
        organization_id="ORG-001",
        identity_id="ID-001",
        position_id="POS-001",
        kernel_id="KERNEL-001",
        capability_ids=[
            "CAP-001",
            "CAP-002",
        ],
        cognitive_function_ids=[
            "CF-PLANNER",
            "CF-REVIEWER",
        ],
        employment_type="FULL_TIME",
        metadata={
            "managed_by": "AI5R",
        },
    )

    assert employee.object_type == "DIGITAL_EMPLOYEE"
    assert employee.employee_name == "CEO AI"
    assert employee.status == "ACTIVE"
    assert employee.employment_type == "FULL_TIME"
    assert employee.employee_id.startswith("EMP-")
    assert employee.kernel_id == "KERNEL-001"
    assert len(employee.capability_ids) == 2
