import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from WORKFORCE.digital_employee_factory import DigitalEmployeeFactory


def test_digital_employee_factory():

    result = DigitalEmployeeFactory().manufacture(
        employee_name="CEO AI",
        organization_id="ORG-001",
        identity_id="ID-001",
        position_id="POS-001",
        kernel_id="KERNEL-001",
        capability_ids=["CAP-001"],
        cognitive_function_ids=["CF-PLANNER"],
        metadata={
            "managed_by":"AI5R",
        },
    )

    employee = result["employee"]

    assert result["status"] == "MANUFACTURED"
    assert employee.object_type == "DIGITAL_EMPLOYEE"
    assert employee.employee_name == "CEO AI"
    assert employee.kernel_id == "KERNEL-001"
