import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.enterprise_kernel import EnterpriseKernel


def test_enterprise_kernel():

    kernel = EnterpriseKernel()

    assert kernel.object_type == "ENTERPRISE_KERNEL"
    assert kernel.status == "INITIALIZED"
    assert kernel.kernel_id.startswith("KERNEL-")

    assert kernel.identity_runtime is None
    assert kernel.position_runtime is None
    assert kernel.decision_runtime is None
    assert kernel.execution_runtime is None
