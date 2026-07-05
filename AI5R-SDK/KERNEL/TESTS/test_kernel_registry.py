import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from KERNEL.kernel_builder import KernelBuilder
from KERNEL.kernel_registry import KernelRegistry


def test_kernel_registry():

    kernel = KernelBuilder().build()
    registry = KernelRegistry()

    registration = registry.register(kernel)

    assert registration["status"] == "REGISTERED"
    assert registration["kernel_id"] == kernel.kernel_id
    assert registry.get(kernel.kernel_id) == kernel
    assert registry.list_all() == [kernel]
    assert registry.list_by_status("INITIALIZED") == [kernel]
