import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXECUTION.execution_engine import ExecutionEngine


def test_execution_engine():

    engine = ExecutionEngine()

    execution = engine.create_execution(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code="CAP-005",
        input_data={"asset_id": "PUMP-001"},
        metadata={"owner": "AI5R"},
    )

    assert execution.object_type == "EXECUTION"
    assert execution.status == "PENDING"
    assert execution.plan_id == "PLAN-001"
    assert execution.step_number == 1
    assert execution.action == "Inspect Pump"
    assert execution.capability_code == "CAP-005"
    assert execution.input_data["asset_id"] == "PUMP-001"
    assert execution.metadata["owner"] == "AI5R"

    print("EX-002 Execution Engine OK")


if __name__ == "__main__":
    test_execution_engine()
