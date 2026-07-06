from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Set


class WorkflowDependencyGraph:
    """
    Dependency graph for workflow execution.

    Public contracts of Workflow and WorkflowStep are intentionally
    untouched (Architecture v2 Frozen).
    """

    def __init__(self):
        self._dependencies: Dict[str, Set[str]] = {}
        self._nodes: Set[str] = set()

    def add_step(self, step_id: str) -> None:
        self._nodes.add(step_id)
        self._dependencies.setdefault(step_id, set())

    def add_dependency(self, step_id: str, depends_on: str) -> None:
        self.add_step(step_id)
        self.add_step(depends_on)
        self._dependencies[step_id].add(depends_on)

    def dependencies_of(self, step_id: str) -> List[str]:
        return sorted(self._dependencies.get(step_id, set()))

    def ready_steps(self, completed: Iterable[str]) -> List[str]:
        completed = set(completed)

        ready = []

        for node in sorted(self._nodes):
            if node in completed:
                continue

            deps = self._dependencies.get(node, set())

            if deps.issubset(completed):
                ready.append(node)

        return ready

    def topological_order(self) -> List[str]:
        indegree = {n: 0 for n in self._nodes}
        outgoing = {n: set() for n in self._nodes}

        for node, deps in self._dependencies.items():
            indegree[node] = len(deps)

            for dep in deps:
                outgoing.setdefault(dep, set()).add(node)

        queue = deque(sorted(n for n, d in indegree.items() if d == 0))
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for nxt in sorted(outgoing.get(node, ())):
                indegree[nxt] -= 1

                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(result) != len(self._nodes):
            raise ValueError("Workflow dependency cycle detected")

        return result
