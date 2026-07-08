from dataclasses import dataclass, field
from typing import Any

from MANUFACTURING import (
    ManufacturingOrder,
    ManufacturingRecipe,
    ProductionLine,
)
from RUNTIME.runtime_engine import (
    RuntimeEngine,
    RuntimeResponse,
)


@dataclass(frozen=True)
class ManufacturingRuntimeAdapter:
    engine: RuntimeEngine
    profile: str = "manufacturing"
    metadata: dict[str, Any] = field(default_factory=dict)

    def execute_order(
        self,
        order: ManufacturingOrder,
        recipe: ManufacturingRecipe,
        line: ProductionLine,
    ) -> RuntimeResponse:
        if not order.validate():
            raise ValueError("manufacturing order is invalid")
        if not recipe.validate():
            raise ValueError("manufacturing recipe is invalid")
        if not line.validate():
            raise ValueError("production line is invalid")
        if order.product_type != recipe.product_type:
            raise ValueError("order and recipe product type mismatch")
        if recipe.production_line_id != line.line_id:
            raise ValueError("recipe and production line mismatch")

        return self.engine.execute_pipeline(
            profile=self.profile,
            definitions=line.station_ids,
            payload={
                "order_id": order.order_id,
                "product_name": order.product_name,
                "product_type": order.product_type,
                "recipe_id": recipe.recipe_id,
                "dbom_id": recipe.dbom_id,
                "requirements": order.requirements,
            },
            metadata={
                "adapter": "ManufacturingRuntimeAdapter",
                "recipe_version": recipe.version,
                **self.metadata,
                **order.metadata,
                **recipe.metadata,
                **line.metadata,
            },
        )
