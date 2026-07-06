import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_WORKFLOW import WorkflowDependencyGraph


def test_dependency_graph_returns_execution_order():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("C", "B")
    graph.add_dependency("B", "A")

    assert graph.topological_order() == [
        "A",
        "B",
        "C",
    ]


def test_ready_steps():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("build", "plan")
    graph.add_dependency("deploy", "build")

    assert graph.ready_steps([]) == ["plan"]
    assert graph.ready_steps(["plan"]) == ["build"]
    assert graph.ready_steps(["plan", "build"]) == ["deploy"]


def test_dependencies():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("deploy", "build")
    graph.add_dependency("deploy", "test")

    assert graph.dependencies_of("deploy") == [
        "build",
        "test",
    ]


def test_cycle_detection():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    graph.add_dependency("C", "A")

    with pytest.raises(ValueError):
        graph.topological_order()
