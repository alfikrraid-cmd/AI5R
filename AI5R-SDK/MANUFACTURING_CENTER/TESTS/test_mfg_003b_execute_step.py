from pathlib import Path

from MANUFACTURING import ManufacturingOrder
from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING_CENTER import ManufacturingOrchestrator
from RUNTIME import RuntimeStatus


def test_execute_single_capability():
    factory = DigitalFactory(
        factory_id="DF-001",
        factory_name="Factory",
    )

    factory.register_capability(
        "CAP-001",
        lambda request: {
            **request.payload,
            "executed": True,
        },
    )

    orchestrator = ManufacturingOrchestrator(
        factory=factory,
        workspace=Path("/tmp"),
    )

    order = ManufacturingOrder(
        order_id="MO-001",
        product_name="Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    step = orchestrator._create_steps(
        line=type(
            "DummyLine",
            (),
            {
                "execution_ids": lambda self: ("CAP-001",),
                "execution_count": lambda self: 1,
            },
        )(),
        order=order,
    )[0]

    response = orchestrator._execute_step(
        step=step,
        payload={"hello": "world"},
        metadata={},
    )

    assert response.status == RuntimeStatus.SUCCESS
    assert response.output["executed"] is True
