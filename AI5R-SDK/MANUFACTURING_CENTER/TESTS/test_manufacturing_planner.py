from pathlib import Path

import pytest

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingOrderStatus,
    ManufacturingRecipe,
    ProductionLine,
)
from MANUFACTURING.FACTORY import DigitalFactory

from MANUFACTURING_CENTER.manufacturing_planner import (
    ManufacturingPlanner,
)


def make_factory() -> DigitalFactory:
    factory = DigitalFactory(
        factory_id="DF-PLANNER-001",
        factory_name="AI5R Planner Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-PLANNER-001",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-PLANNER-001",
        production_line_id="LINE-PLANNER-001",
        qa_policy_id="QA-PLANNER-001",
        packaging_id="PKG-PLANNER-001",
        deployment_id="DEPLOY-PLANNER-001",
    )

    line = ProductionLine(
        line_id="LINE-PLANNER-001",
        line_name="Website Production Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENTS",
            "FRONTEND",
            "BACKEND",
            "INTEGRATION",
        ),
        metadata={
            "dependencies": {
                "FRONTEND": ["REQUIREMENTS"],
                "BACKEND": ["REQUIREMENTS"],
                "INTEGRATION": [
                    "FRONTEND",
                    "BACKEND",
                ],
            },
        },
    )

    factory.register_recipe(recipe, line)
    return factory


def make_order(
    *,
    status: ManufacturingOrderStatus = ManufacturingOrderStatus.DRAFT,
) -> ManufacturingOrder:
    return ManufacturingOrder(
        order_id="MO-PLANNER-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Chief",
        status=status,
        metadata={"owner": "Chief"},
    )


def test_planner_builds_manufacturing_plan(tmp_path: Path) -> None:
    planner = ManufacturingPlanner(
        factory=make_factory(),
        workspace=tmp_path,
        metadata={"planner_version": "1.0.0"},
    )

    plan = planner.plan(order=make_order())

    assert plan.plan_id == "PLAN-MO-PLANNER-001"
    assert plan.order.order_id == "MO-PLANNER-001"
    assert plan.recipe.recipe_id == "RCP-PLANNER-001"
    assert plan.line.line_id == "LINE-PLANNER-001"

    assert plan.execution_levels() == (
        ("REQUIREMENTS",),
        ("BACKEND", "FRONTEND"),
        ("INTEGRATION",),
    )

    assert plan.metadata["owner"] == "Chief"
    assert plan.metadata["planner_version"] == "1.0.0"
    assert plan.metadata["workspace"] == str(tmp_path)
    assert plan.is_ready is True


def test_planner_rejects_order_not_ready(tmp_path: Path) -> None:
    planner = ManufacturingPlanner(
        factory=make_factory(),
        workspace=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="order is not ready for planning",
    ):
        planner.plan(
            order=make_order(
                status=ManufacturingOrderStatus.COMPLETED,
            )
        )


def test_planner_rejects_invalid_dependencies(tmp_path: Path) -> None:
    factory = DigitalFactory(
        factory_id="DF-INVALID-001",
        factory_name="Invalid Factory",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-INVALID-001",
        recipe_name="Invalid Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-INVALID-001",
        production_line_id="LINE-INVALID-001",
        qa_policy_id="QA-INVALID-001",
        packaging_id="PKG-INVALID-001",
        deployment_id="DEPLOY-INVALID-001",
    )

    line = ProductionLine(
        line_id="LINE-INVALID-001",
        line_name="Invalid Line",
        product_type="WEBSITE",
        capability_ids=("BUILD",),
        metadata={
            "dependencies": {
                "BUILD": ["UNKNOWN"],
            },
        },
    )

    factory.register_recipe(recipe, line)

    planner = ManufacturingPlanner(
        factory=factory,
        workspace=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="unknown dependency",
    ):
        planner.plan(order=make_order())
