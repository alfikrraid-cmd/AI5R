from __future__ import annotations

from dataclasses import dataclass

from .manufacturing_execution_graph import ManufacturingExecutionGraph


@dataclass(slots=True, frozen=True)
class ManufacturingParallelPlan:
    graph: ManufacturingExecutionGraph

    def execution_levels(self) -> tuple[tuple[str, ...], ...]:
        dependency_map = {
            node: set(dependencies)
            for node, dependencies in self.graph.dependencies.items()
        }

        remaining = set(dependency_map)
        completed: set[str] = set()
        levels: list[tuple[str, ...]] = []

        while remaining:
            ready = tuple(
                sorted(
                    node
                    for node in remaining
                    if dependency_map[node].issubset(completed)
                )
            )

            if not ready:
                raise RuntimeError(
                    "Manufacturing dependency cycle detected."
                )

            levels.append(ready)
            completed.update(ready)
            remaining.difference_update(ready)

        return tuple(levels)

    def level_count(self) -> int:
        return len(self.execution_levels())

    def max_parallelism(self) -> int:
        levels = self.execution_levels()
        return max((len(level) for level in levels), default=0)
