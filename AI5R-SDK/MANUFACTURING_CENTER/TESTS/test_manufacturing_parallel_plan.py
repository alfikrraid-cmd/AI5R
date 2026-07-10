from MANUFACTURING import ProductionLine

from MANUFACTURING_CENTER.manufacturing_execution_graph import (
    ManufacturingExecutionGraph,
)
from MANUFACTURING_CENTER.manufacturing_parallel_plan import (
    ManufacturingParallelPlan,
)


def make_graph() -> ManufacturingExecutionGraph:
    line = ProductionLine(
        line_id="LINE-PARALLEL-001",
        line_name="Parallel Production Line",
        product_type="WEBSITE",
        capability_ids=(
            "REQUIREMENTS",
            "ARCHITECTURE",
            "FRONTEND",
            "BACKEND",
            "INTEGRATION",
            "QA",
        ),
    )

    return ManufacturingExecutionGraph.from_line(
        line,
        dependencies={
            "ARCHITECTURE": ("REQUIREMENTS",),
            "FRONTEND": ("ARCHITECTURE",),
            "BACKEND": ("ARCHITECTURE",),
            "INTEGRATION": ("FRONTEND", "BACKEND"),
            "QA": ("INTEGRATION",),
        },
    )


def test_builds_parallel_execution_levels() -> None:
    plan = ManufacturingParallelPlan(graph=make_graph())

    assert plan.execution_levels() == (
        ("REQUIREMENTS",),
        ("ARCHITECTURE",),
        ("BACKEND", "FRONTEND"),
        ("INTEGRATION",),
        ("QA",),
    )


def test_level_count() -> None:
    plan = ManufacturingParallelPlan(graph=make_graph())

    assert plan.level_count() == 5


def test_max_parallelism() -> None:
    plan = ManufacturingParallelPlan(graph=make_graph())

    assert plan.max_parallelism() == 2


def test_linear_graph_has_single_node_per_level() -> None:
    line = ProductionLine(
        line_id="LINE-LINEAR-001",
        line_name="Linear Line",
        product_type="WEBSITE",
        capability_ids=("A", "B", "C"),
    )

    graph = ManufacturingExecutionGraph.from_line(
        line,
        dependencies={
            "B": ("A",),
            "C": ("B",),
        },
    )

    plan = ManufacturingParallelPlan(graph=graph)

    assert plan.execution_levels() == (
        ("A",),
        ("B",),
        ("C",),
    )
    assert plan.max_parallelism() == 1
