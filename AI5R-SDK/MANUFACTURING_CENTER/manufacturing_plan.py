from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from MANUFACTURING.LINES import ProductionLine
from MANUFACTURING.ORDERS import ManufacturingOrder
from MANUFACTURING.RECIPES import ManufacturingRecipe

from .manufacturing_execution_graph import ManufacturingExecutionGraph
from .manufacturing_parallel_plan import ManufacturingParallelPlan


@dataclass(slots=True, kw_only=True)
class ManufacturingPlan:
    plan_id: str
    order: ManufacturingOrder
    recipe: ManufacturingRecipe
    line: ProductionLine
    execution_graph: ManufacturingExecutionGraph
    parallel_plan: ManufacturingParallelPlan
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.plan_id = self.plan_id.strip()

        if not self.plan_id:
            raise ValueError("plan_id must not be empty")

        if not self.order.validate():
            raise ValueError("order is invalid")

        if not self.recipe.validate():
            raise ValueError("recipe is invalid")

        if not self.line.validate():
            raise ValueError("production line is invalid")

        if self.order.product_type != self.recipe.product_type:
            raise ValueError(
                "order and recipe product type mismatch"
            )

        if self.recipe.product_type != self.line.product_type:
            raise ValueError(
                "recipe and production line product type mismatch"
            )

        if self.recipe.production_line_id != self.line.line_id:
            raise ValueError(
                "recipe and production line mismatch"
            )

        if self.execution_graph.line.line_id != self.line.line_id:
            raise ValueError(
                "execution graph and production line mismatch"
            )

        if self.parallel_plan.graph is not self.execution_graph:
            raise ValueError(
                "parallel plan must use execution_graph"
            )

        self.metadata = dict(self.metadata)

    @property
    def is_ready(self) -> bool:
        return bool(
            self.order.is_ready_for_planning()
            and self.recipe.is_ready()
            and self.line.validate()
            and self.execution_graph.execution_order()
            and self.parallel_plan.execution_levels()
        )

    def execution_order(self) -> tuple[str, ...]:
        return self.execution_graph.execution_order()

    def execution_levels(self) -> tuple[tuple[str, ...], ...]:
        return self.parallel_plan.execution_levels()

    def summary(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "order_id": self.order.order_id,
            "product_type": self.order.product_type,
            "recipe_id": self.recipe.recipe_id,
            "line_id": self.line.line_id,
            "execution_count": len(self.execution_order()),
            "level_count": self.parallel_plan.level_count(),
            "max_parallelism": self.parallel_plan.max_parallelism(),
        }
