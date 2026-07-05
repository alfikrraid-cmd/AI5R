import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.BASELINE.kernel_baseline import KernelBaseline


def test_kernel_baseline_version():
    assert KernelBaseline.VERSION == "1.0.0"


def test_kernel_baseline_passes():
    result = KernelBaseline.verify()

    assert result["status"] == "PASS"
    assert result["missing"] == []


def test_kernel_baseline_contains_required_components():
    result = KernelBaseline.verify()

    expected = {
        "identity",
        "object",
        "event",
        "pipeline",
        "registry",
        "runtime",
    }

    assert set(result["components"]) == expected


def test_kernel_component_count():
    result = KernelBaseline.verify()

    assert len(result["components"]) == 6
