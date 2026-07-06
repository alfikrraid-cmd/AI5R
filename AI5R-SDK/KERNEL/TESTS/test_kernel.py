import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL import AI5RKernel


def test_kernel_boot():

    kernel = AI5RKernel()

    assert kernel.status == "STOPPED"

    kernel.boot()

    assert kernel.is_running()

    kernel.shutdown()

    assert kernel.status == "STOPPED"
