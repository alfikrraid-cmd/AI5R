import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from PRODUCTS.LTSA_BRAIN.work_order_generator import WorkOrderGenerator


def test_work_order_generator_creates_work_order():
    generator = WorkOrderGenerator()

    decision = {
        "decision": "REPLACE_BEARING",
        "priority": "CRITICAL",
        "reason": "Critical failure detected.",
        "next_step": "Generate Work Order",
    }

    work_order = generator.generate(
        asset="P-101",
        decision=decision,
    )

    assert work_order["object_type"] == "work_order"
    assert work_order["asset"] == "P-101"
    assert work_order["priority"] == "CRITICAL"
    assert work_order["status"] == "OPEN"
    assert "Replace bearing" in work_order["tasks"]

    print("LTSA-010 Work Order Generator OK")


if __name__ == "__main__":
    test_work_order_generator_creates_work_order()
