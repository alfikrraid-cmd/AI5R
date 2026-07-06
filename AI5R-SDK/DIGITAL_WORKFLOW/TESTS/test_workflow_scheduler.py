import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from DIGITAL_WORKFLOW import (
    WorkflowDependencyGraph,
    WorkflowScheduler,
)


def test_execution_plan():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("C", "B")
    graph.add_dependency("B", "A")

    scheduler = WorkflowScheduler(graph)

    assert scheduler.execution_plan() == [
        "A",
        "B",
        "C",
    ]


def test_next_steps():
    graph = WorkflowDependencyGraph()

    graph.add_dependency("compile", "design")
    graph.add_dependency("deploy", "compile")

    scheduler = WorkflowScheduler(graph)

    assert scheduler.next_steps([]) == ["design"]
    assert scheduler.next_steps(["design"]) == ["compile"]
    assert scheduler.next_steps(["design", "compile"]) == ["deploy"]


def test_parallel_batches():
    graph = WorkflowDependencyGraph()

    graph.add_step("A")
    graph.add_dependency("B", "A")
    graph.add_dependency("C", "A")
    graph.add_dependency("D", "B")
    graph.add_dependency("D", "C")

    scheduler = WorkflowScheduler(graph)

    assert scheduler.execution_batches() == [
        ["A"],
        ["B", "C"],
        ["D"],
    ]
