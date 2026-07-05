import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_runtime import KernelRuntime


def test_kernel_runtime_create_unhealthy():

    runtime = KernelRuntime()

    result = runtime.create()

    kernel = result["kernel"]

    assert result["status"] == "CREATED"
    assert result["health"]["status"] == "UNHEALTHY"
    assert result["registration"]["status"] == "REGISTERED"

    assert runtime.get(kernel.kernel_id) == kernel
    assert runtime.list_all() == [kernel]
    assert runtime.list_by_status("INITIALIZED") == [kernel]


def test_kernel_runtime_create_healthy():

    runtime = KernelRuntime()

    result = runtime.create(
        identity_runtime="IDENTITY_RUNTIME",
        position_runtime="POSITION_RUNTIME",
        decision_runtime="DECISION_RUNTIME",
        execution_runtime="EXECUTION_RUNTIME",
    )

    assert result["status"] == "CREATED"
    assert result["health"]["status"] == "HEALTHY"
