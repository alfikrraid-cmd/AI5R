from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext


def test_context_creation():
    context = ManufacturingContext(
        build_id="BUILD-001",
        product="LTSA-BRAIN",
        version="1.0",
    )

    assert context.build_id == "BUILD-001"
    assert context.product == "LTSA-BRAIN"
    assert context.version == "1.0"


def test_add_asset():
    context = ManufacturingContext(
        build_id="1",
        product="AI5R",
        version="1",
    )

    context.add_asset("worker.py")

    assert len(context.generated_assets) == 1


def test_add_report():
    context = ManufacturingContext(
        build_id="1",
        product="AI5R",
        version="1",
    )

    context.add_report(
        "validation",
        {"status": "VALID"},
    )

    assert context.reports["validation"]["status"] == "VALID"


def test_freeze():
    context = ManufacturingContext(
        build_id="1",
        product="AI5R",
        version="1",
    )

    assert context.frozen is False

    context.freeze()

    assert context.frozen is True
