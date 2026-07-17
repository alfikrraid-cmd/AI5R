import tempfile
from pathlib import Path

from MANUFACTURING import (
    ManufacturingOrder,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING_CENTER import ManufacturingOrchestrator


def test_create_steps_from_capabilities():
    factory = DigitalFactory(
        factory_id="DF-001",
        factory_name="AI5R Factory",
    )

    orchestrator = ManufacturingOrchestrator(
        factory=factory,
        workspace=Path(tempfile.gettempdir()),
    )

    order = ManufacturingOrder(
        order_id="MO-001",
        product_name="Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    line = ProductionLine(
        line_id="LINE-001",
        line_name="Website",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENT_ANALYSIS",
            "ARCHITECTURE_DESIGN",
            "QA",
        ),
    )

    steps = orchestrator._create_steps(
        line=line,
        order=order,
    )

    assert len(steps) == 3
    assert steps[0].capability_id == "REQUIREMENT_ANALYSIS"
    assert steps[1].capability_id == "ARCHITECTURE_DESIGN"
    assert steps[2].capability_id == "QA"
    assert steps[0].metadata["sequence"] == 1
    assert steps[2].metadata["total_steps"] == 3
