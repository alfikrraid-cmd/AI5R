from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CycleDetectionResult:
    cycles: list[list[str]] = field(default_factory=list)

    @property
    def has_cycle(self) -> bool:
        return len(self.cycles) > 0


class CircularDependencyDetector:
    def __init__(self, graph: dict[str, list[str]]):
        self.graph = graph

    def detect(self) -> CycleDetectionResult:
        visited = set()
        stack = set()
        path = []
        result = CycleDetectionResult()

        def dfs(node: str):
            if node in stack:
                cycle_start = path.index(node)
                result.cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, []):
                dfs(neighbor)

            stack.remove(node)
            path.pop()

        for node in self.graph:
            dfs(node)

        return result
