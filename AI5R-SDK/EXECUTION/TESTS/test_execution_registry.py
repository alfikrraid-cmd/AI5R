import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXECUTION.execution_engine import ExecutionEngine
from EXECUTION.execution_registry import ExecutionRegistry


def test_execution_registry():

    engine = ExecutionEngine()
    registry = ExecutionRegistry()

    execution = engine.create_execution(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code="CAP-005",
        input_data={"asset_id": "PUMP-001"},
    )

    registration = registry.register(execution)

    assert registration["status"] == "REGISTERED"
    assert registration["execution_id"] == execution.execution_id
    assert registry.get(execution.execution_id) == execution
    assert registry.list_all() == [execution]
    assert registry.list_by_plan("PLAN-001") == [execution]
    assert registry.list_by_status("PENDING") == [execution]

    print("EX-003 Execution Registry OK")


if __name__ == "__main__":
    test_execution_registry()
