import pytest

from MANUFACTURING import ProductionLine
from MANUFACTURING_CENTER.manufacturing_execution_graph import (
    ManufacturingExecutionGraph,
)


def make_line() -> ProductionLine:
    return ProductionLine(
        line_id="LINE-GRAPH-001",
        line_name="Graph Production Line",
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


def test_linear_order_without_dependencies() -> None:
    graph = ManufacturingExecutionGraph.from_line(make_line())

    assert graph.execution_order() == (
        "REQUIREMENTS",
        "ARCHITECTURE",
        "FRONTEND",
        "BACKEND",
        "INTEGRATION",
        "QA",
    )


def test_orders_capabilities_by_dependencies() -> None:
    graph = ManufacturingExecutionGraph.from_line(
        make_line(),
        dependencies={
            "ARCHITECTURE": ("REQUIREMENTS",),
            "FRONTEND": ("ARCHITECTURE",),
            "BACKEND": ("ARCHITECTURE",),
            "INTEGRATION": ("FRONTEND", "BACKEND"),
            "QA": ("INTEGRATION",),
        },
    )

    order = graph.execution_order()

    assert order.index("REQUIREMENTS") < order.index("ARCHITECTURE")
    assert order.index("ARCHITECTURE") < order.index("FRONTEND")
    assert order.index("ARCHITECTURE") < order.index("BACKEND")
    assert order.index("FRONTEND") < order.index("INTEGRATION")
    assert order.index("BACKEND") < order.index("INTEGRATION")
    assert order.index("INTEGRATION") < order.index("QA")


def test_detects_dependency_cycle() -> None:
    graph = ManufacturingExecutionGraph.from_line(
        make_line(),
        dependencies={
            "REQUIREMENTS": ("QA",),
            "QA": ("REQUIREMENTS",),
        },
    )

    with pytest.raises(
        RuntimeError,
        match="dependency cycle",
    ):
        graph.execution_order()


def test_rejects_unknown_dependency() -> None:
    with pytest.raises(
        ValueError,
        match="unknown dependency",
    ):
        ManufacturingExecutionGraph.from_line(
            make_line(),
            dependencies={
                "QA": ("DOES_NOT_EXIST",),
            },
        )


def test_rejects_unknown_graph_node() -> None:
    with pytest.raises(
        ValueError,
        match="unknown capability",
    ):
        ManufacturingExecutionGraph.from_line(
            make_line(),
            dependencies={
                "UNKNOWN": (),
            },
        )


def test_rejects_self_dependency() -> None:
    with pytest.raises(
        ValueError,
        match="cannot depend on itself",
    ):
        ManufacturingExecutionGraph.from_line(
            make_line(),
            dependencies={
                "QA": ("QA",),
            },
        )


def test_metadata() -> None:
    graph = ManufacturingExecutionGraph.from_line(
        make_line(),
        dependencies={
            "ARCHITECTURE": ("REQUIREMENTS",),
            "QA": ("INTEGRATION",),
        },
    )

    assert graph.metadata() == {
        "line_id": "LINE-GRAPH-001",
        "execution_count": 6,
        "dependency_count": 2,
    }
