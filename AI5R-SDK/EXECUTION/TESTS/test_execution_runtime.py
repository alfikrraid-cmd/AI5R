import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from EXECUTION.execution_runtime import ExecutionRuntime


def test_execution_runtime():

    runtime = ExecutionRuntime()

    result = runtime.create(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code="CAP-005",
        input_data={
            "asset_id": "PUMP-001",
        },
        metadata={
            "owner": "AI5R",
        },
    )

    execution = result["execution"]

    assert result["status"] == "CREATED"
    assert result["registration"]["status"] == "REGISTERED"

    assert runtime.get(execution.execution_id) == execution
    assert runtime.list_all() == [execution]
    assert runtime.list_by_plan("PLAN-001") == [execution]
    assert runtime.list_by_status("PENDING") == [execution]

    print("EX-004 Execution Runtime OK")


if __name__ == "__main__":
    test_execution_runtime()
