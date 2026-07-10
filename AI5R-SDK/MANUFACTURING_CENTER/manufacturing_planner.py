from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from MANUFACTURING.FACTORY import DigitalFactory
from MANUFACTURING.ORDERS import ManufacturingOrder

from .manufacturing_execution_graph import ManufacturingExecutionGraph
from .manufacturing_parallel_plan import ManufacturingParallelPlan
from .manufacturing_plan import ManufacturingPlan


@dataclass(slots=True)
class ManufacturingPlanner:
    factory: DigitalFactory
    workspace: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace, Path):
            raise TypeError("workspace must be a Path")

        if not self.workspace.is_absolute():
            raise ValueError("workspace must be absolute")

        if not self.factory.validate():
            raise ValueError("factory is invalid")

        self.metadata = dict(self.metadata)

    def plan(
        self,
        *,
        order: ManufacturingOrder,
    ) -> ManufacturingPlan:

        if not order.is_ready_for_planning():
            raise ValueError("order is not ready for planning")

        recipe = self.factory.get_recipe(order.product_type)
        line = self.factory.get_line(recipe.production_line_id)

        raw_dependencies = line.metadata.get("dependencies", {})
        if not isinstance(raw_dependencies, dict):
            raise TypeError("dependencies must be a dict")

        dependencies: dict[str, tuple[str, ...]] = {}

        execution_ids = set(line.execution_ids())

        for capability, values in raw_dependencies.items():

            if capability not in execution_ids:
                raise ValueError(
                    f"unknown capability '{capability}'"
                )

            if isinstance(values, str):
                values = (values,)
            else:
                values = tuple(values)

            for dependency in values:
                if dependency not in execution_ids:
                    raise ValueError(
                        f"unknown dependency '{dependency}'"
                    )

            dependencies[capability] = values

        graph = ManufacturingExecutionGraph.from_line(
            line,
            dependencies=dependencies,
        )

        parallel_plan = ManufacturingParallelPlan(
            graph=graph,
        )

        merged_metadata = {
            **self.metadata,
            **order.metadata,
            "workspace": str(self.workspace),
        }

        return ManufacturingPlan(
            plan_id=f"PLAN-{order.order_id}",
            order=order,
            recipe=recipe,
            line=line,
            execution_graph=graph,
            parallel_plan=parallel_plan,
            metadata=merged_metadata,
        )
