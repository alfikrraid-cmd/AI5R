from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)

from MANUFACTURING_CENTER.manufacturing_execution_graph import (
    ManufacturingExecutionGraph,
)
from MANUFACTURING_CENTER.manufacturing_parallel_plan import (
    ManufacturingParallelPlan,
)
from MANUFACTURING_CENTER.manufacturing_plan import ManufacturingPlan


def make_plan() -> ManufacturingPlan:
    order = ManufacturingOrder(
        order_id="MO-PLAN-001",
        product_name="AI5R Website",
        product_type="WEBSITE",
        requested_by="Chief",
    )

    recipe = ManufacturingRecipe(
        recipe_id="RCP-PLAN-001",
        recipe_name="Website Recipe",
        product_type="WEBSITE",
        dbom_id="DBOM-PLAN-001",
        production_line_id="LINE-PLAN-001",
        qa_policy_id="QA-PLAN-001",
        packaging_id="PKG-PLAN-001",
        deployment_id="DEPLOY-PLAN-001",
    )

    line = ProductionLine(
        line_id="LINE-PLAN-001",
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
                "INTEGRATION": ["FRONTEND", "BACKEND"],
            },
        },
    )

    graph = ManufacturingExecutionGraph.from_line(
        line,
        dependencies={
            "FRONTEND": ("REQUIREMENTS",),
            "BACKEND": ("REQUIREMENTS",),
            "INTEGRATION": ("FRONTEND", "BACKEND"),
        },
    )

    parallel_plan = ManufacturingParallelPlan(graph=graph)

    return ManufacturingPlan(
        plan_id="PLAN-MO-PLAN-001",
        order=order,
        recipe=recipe,
        line=line,
        execution_graph=graph,
        parallel_plan=parallel_plan,
        metadata={"planner": "ManufacturingPlanner"},
    )


def test_create_manufacturing_plan() -> None:
    plan = make_plan()

    assert plan.plan_id == "PLAN-MO-PLAN-001"
    assert plan.order.order_id == "MO-PLAN-001"
    assert plan.recipe.recipe_id == "RCP-PLAN-001"
    assert plan.line.line_id == "LINE-PLAN-001"
    order = plan.execution_order()

    assert order[0] == "REQUIREMENTS"
    assert order[-1] == "INTEGRATION"
    assert set(order[1:3]) == {
        "FRONTEND",
        "BACKEND",
    }
    assert plan.execution_levels() == (
        ("REQUIREMENTS",),
        ("BACKEND", "FRONTEND"),
        ("INTEGRATION",),
    )


def test_plan_is_ready() -> None:
    plan = make_plan()

    assert plan.is_ready is True


def test_plan_summary() -> None:
    plan = make_plan()

    assert plan.summary() == {
        "plan_id": "PLAN-MO-PLAN-001",
        "order_id": "MO-PLAN-001",
        "product_type": "WEBSITE",
        "recipe_id": "RCP-PLAN-001",
        "line_id": "LINE-PLAN-001",
        "execution_count": 4,
        "level_count": 3,
        "max_parallelism": 2,
    }
