import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_builder import KernelBuilder


def test_kernel_builder():

    builder = KernelBuilder()

    kernel = builder.build(
        identity_runtime="IDENTITY_RUNTIME",
        position_runtime="POSITION_RUNTIME",
        decision_runtime="DECISION_RUNTIME",
        execution_runtime="EXECUTION_RUNTIME",
    )

    assert kernel.object_type == "ENTERPRISE_KERNEL"
    assert kernel.status == "INITIALIZED"
    assert kernel.identity_runtime == "IDENTITY_RUNTIME"
    assert kernel.position_runtime == "POSITION_RUNTIME"
    assert kernel.decision_runtime == "DECISION_RUNTIME"
    assert kernel.execution_runtime == "EXECUTION_RUNTIME"
