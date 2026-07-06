import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from AI5R_KERNEL import AI5RKernel


def test_ai5r_kernel_manufactures_product():
    kernel = AI5RKernel()

    result = kernel.manufacture("Digital Employee")

    assert result["status"] == "MANUFACTURED"
    assert result["product"] == "DIGITAL_EMPLOYEE"

    assert result["payload"]["specification"]["status"] == "SPECIFIED"
    assert result["payload"]["factory"]["status"] == "BUILT"
    assert result["payload"]["assembly"]["status"] == "ASSEMBLED"
    assert result["payload"]["artifact"]["status"] == "MANUFACTURED"
    assert result["payload"]["registry"]["status"] == "REGISTERED"
    assert result["payload"]["runtime"]["status"] == "RUNNING"
    assert result["payload"]["release"]["status"] == "RELEASED"

    assert len(result["history"]) == 7


def test_ai5r_kernel_accepts_initial_payload():
    kernel = AI5RKernel()

    result = kernel.manufacture(
        "Digital School",
        payload={
            "source": "test",
        },
    )

    assert result["product"] == "DIGITAL_SCHOOL"
    assert result["payload"]["source"] == "test"
    assert result["payload"]["release"]["status"] == "RELEASED"
