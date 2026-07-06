import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from CAPABILITY.capability_object import CapabilityObject
from CAPABILITY.capability_runtime import CapabilityRuntime
from EXECUTION.execution_runtime import ExecutionRuntime
from INTEGRATION.execution_dispatcher import ExecutionDispatcher


def test_execution_dispatcher():

    capability_runtime = CapabilityRuntime()

    capability = CapabilityObject(
        organization_id="ORG-001",
        capability_code="CAP-005",
        capability_name="Pump Inspection",
        description="Pump inspection capability",
        supported_domains=["maintenance"],
    )

    capability_runtime.register(capability)

    execution_runtime = ExecutionRuntime()

    execution = execution_runtime.create(
        plan_id="PLAN-001",
        step_number=1,
        action="Inspect Pump",
        capability_code=capability.capability_id,
        input_data={
            "asset_id": "PUMP-001",
        },
    )["execution"]

    dispatcher = ExecutionDispatcher()

    dispatcher.capability_runtime = capability_runtime

    result = dispatcher.dispatch(execution)

    assert result["status"] == "DISPATCHED"
    assert result["execution_id"] == execution.execution_id
    assert result["capability_result"]["status"] == "EXECUTED"

    print("EI-004 Execution Dispatcher OK")


if __name__ == "__main__":
    test_execution_dispatcher()
