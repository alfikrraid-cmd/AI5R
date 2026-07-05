import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXECUTION.execution_object import ExecutionObject


def test_execution_object():

    execution = ExecutionObject(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code="CAP-005",
        input_data={
            "asset_id": "PUMP-001"
        },
    )

    assert execution.object_type == "EXECUTION"
    assert execution.status == "PENDING"
    assert execution.step_number == 1
    assert execution.capability_code == "CAP-005"
    assert execution.input_data["asset_id"] == "PUMP-001"

    print("EX-001 Execution Object OK")


if __name__ == "__main__":
    test_execution_object()
