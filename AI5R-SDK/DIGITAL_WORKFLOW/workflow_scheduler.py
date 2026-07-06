from __future__ import annotations

from collections import deque
from typing import Iterable, List

from .workflow_dependency_graph import WorkflowDependencyGraph


class WorkflowScheduler:
    """
    Determines which workflow steps are executable next.

    Stateless and backward compatible.
    """

    def __init__(self, graph: WorkflowDependencyGraph):
        self._graph = graph

    def next_steps(self, completed: Iterable[str]) -> List[str]:
        return self._graph.ready_steps(completed)

    def execution_plan(self) -> List[str]:
        return self._graph.topological_order()

    def execution_batches(self) -> List[List[str]]:
        graph = self._graph

        completed = set()
        batches = []

        while True:
            ready = graph.ready_steps(completed)

            ready = [s for s in ready if s not in completed]

            if not ready:
                break

            batches.append(sorted(ready))
            completed.update(ready)

        if len(completed) != len(graph.topological_order()):
            raise ValueError("Workflow scheduling failed")

        return batches
