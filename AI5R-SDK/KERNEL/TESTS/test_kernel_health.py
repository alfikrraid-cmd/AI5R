import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_builder import KernelBuilder
from KERNEL.kernel_health import KernelHealth


def test_kernel_health_unhealthy():

    kernel = KernelBuilder().build()

    result = KernelHealth().check(kernel)

    assert result["status"] == "UNHEALTHY"
    assert "identity_runtime" in result["missing"]


def test_kernel_health_healthy():

    kernel = KernelBuilder().build(
        identity_runtime="IDENTITY_RUNTIME",
        position_runtime="POSITION_RUNTIME",
        decision_runtime="DECISION_RUNTIME",
        execution_runtime="EXECUTION_RUNTIME",
    )

    result = KernelHealth().check(kernel)

    assert result["status"] == "HEALTHY"
    assert result["missing"] == []
