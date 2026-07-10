from pathlib import Path

from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.LINES import ProductionLine
from MANUFACTURING.ORDERS import ManufacturingOrder
from MANUFACTURING.RECIPES import ManufacturingRecipe
from MANUFACTURING_CENTER.manufacturing_center import ManufacturingCenter
from MANUFACTURING_CENTER.manufacturing_status import ManufacturingStatus


def test_graph_orchestrator_executes_capability_order(tmp_path: Path) -> None:
    execution_order: list[str] = []

    factory = DigitalFactory(
        factory_id="DF-001",
        factory_name="AI5R Factory",
    )

    line = ProductionLine(
        line_id="LINE-001",
        line_name="Website Line",
        product_type="WEBSITE",
        capability_ids=(
            "QA",
            "IMPLEMENTATION",
            "ARCHITECTURE",
            "REQUIREMENTS",
        ),
        metadata={
            "dependencies": {
                "ARCHITECTURE": ["REQUIREMENTS"],
                "IMPLEMENTATION": ["ARCHITECTURE"],
                "QA": ["IMPLEMENTATION"],
            },
        },
    )

    recipe = ManufacturingRecipe(
        recipe_id="RECIPE-001",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-001",
        production_line_id="LINE-001",
        qa_policy_id="QA-001",
        packaging_id="PKG-001",
        deployment_id="DEPLOY-001",
    )

    factory.register_recipe(recipe, line)

    for capability in line.capability_ids:

        def handler(request, capability=capability):
            execution_order.append(capability)
            payload = dict(request.payload)
            payload[capability.lower()] = True
            return payload

        factory.register_capability(capability, handler)

    order = ManufacturingOrder(
        order_id="MO-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    center = ManufacturingCenter(
        factory=factory,
        workspace=tmp_path.resolve(),
    )

    result = center.manufacture(order=order)

    assert result.status == ManufacturingStatus.COMPLETED

    assert execution_order == [
        "REQUIREMENTS",
        "ARCHITECTURE",
        "IMPLEMENTATION",
        "QA",
    ]
