from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from FACTORY.MANUFACTURING.topological_sort import TopologicalSorter
from MANUFACTURING.LINES import ProductionLine


@dataclass(slots=True, kw_only=True)
class ManufacturingExecutionGraph:
    line: ProductionLine
    dependencies: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.line.validate():
            raise ValueError("production line is invalid")

        execution_ids = self.line.execution_ids()
        known_ids = set(execution_ids)

        copied_dependencies: dict[str, tuple[str, ...]] = {}

        for capability_id in execution_ids:
            raw_dependencies = self.dependencies.get(capability_id, ())
            dependencies = tuple(raw_dependencies)

            for dependency in dependencies:
                if dependency not in known_ids:
                    raise ValueError(
                        f"unknown dependency {dependency!r} "
                        f"for capability {capability_id!r}"
                    )

                if dependency == capability_id:
                    raise ValueError(
                        f"capability {capability_id!r} "
                        "cannot depend on itself"
                    )

            copied_dependencies[capability_id] = dependencies

        unknown_nodes = set(self.dependencies) - known_ids
        if unknown_nodes:
            unknown = sorted(unknown_nodes)[0]
            raise ValueError(
                f"dependency graph contains unknown capability {unknown!r}"
            )

        self.dependencies = copied_dependencies

    @classmethod
    def from_line(
        cls,
        line: ProductionLine,
        *,
        dependencies: dict[str, tuple[str, ...]] | None = None,
    ) -> ManufacturingExecutionGraph:
        return cls(
            line=line,
            dependencies=dict(dependencies or {}),
        )

    def as_graph(self) -> dict[str, list[str]]:
        return {
            capability_id: list(self.dependencies[capability_id])
            for capability_id in self.line.execution_ids()
        }

    def execution_order(self) -> tuple[str, ...]:
        if not any(self.dependencies.values()):
            return tuple(self.line.execution_ids())

        ordered = TopologicalSorter().sort(self.as_graph())
        return tuple(ordered)

    def dependency_count(self, capability_id: str) -> int:
        if capability_id not in self.dependencies:
            raise KeyError(capability_id)

        return len(self.dependencies[capability_id])

    def metadata(self) -> dict[str, Any]:
        return {
            "line_id": self.line.line_id,
            "execution_count": self.line.execution_count(),
            "dependency_count": sum(
                len(values) for values in self.dependencies.values()
            ),
        }
