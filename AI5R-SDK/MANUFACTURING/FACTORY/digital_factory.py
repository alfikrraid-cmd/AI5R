from dataclasses import dataclass, field
from typing import Any

from MANUFACTURING.FACTORY.factory_registry import FactoryRegistry
from MANUFACTURING.LINES import ProductionLine
from MANUFACTURING.ORDERS import ManufacturingOrder
from MANUFACTURING.RECIPES import ManufacturingRecipe
from RUNTIME.ADAPTERS.manufacturing_adapter import ManufacturingRuntimeAdapter
from RUNTIME.runtime_engine import (
    RuntimeEngine,
    RuntimeResponse,
)


@dataclass
class DigitalFactory:
    factory_id: str
    factory_name: str
    engine: RuntimeEngine = field(default_factory=RuntimeEngine)
    profile: str = "manufacturing"
    metadata: dict[str, Any] = field(default_factory=dict)
    registry: FactoryRegistry = field(default_factory=FactoryRegistry)

    def validate(self) -> bool:
        return bool(
            self.factory_id
            and self.factory_name
            and self.profile
        )

    def register_recipe(
        self,
        recipe: ManufacturingRecipe,
        line: ProductionLine,
    ) -> None:
        self.registry.register_recipe(recipe, line)

    def get_recipe(self, product_type: str) -> ManufacturingRecipe:
        return self.registry.get_recipe(product_type)

    def get_line(self, line_id: str) -> ProductionLine:
        return self.registry.get_line(line_id)

    def manufacture(
        self,
        order: ManufacturingOrder,
        recipe: ManufacturingRecipe,
        line: ProductionLine,
    ) -> RuntimeResponse:
        if not self.validate():
            raise ValueError("digital factory is invalid")

        adapter = ManufacturingRuntimeAdapter(
            engine=self.engine,
            profile=self.profile,
            metadata={
                "factory_id": self.factory_id,
                "factory_name": self.factory_name,
                **self.metadata,
            },
        )

        return adapter.execute_order(
            order=order,
            recipe=recipe,
            line=line,
        )

    def manufacture_order(
        self,
        order: ManufacturingOrder,
    ) -> RuntimeResponse:
        recipe = self.get_recipe(order.product_type)
        line = self.get_line(recipe.production_line_id)

        return self.manufacture(
            order=order,
            recipe=recipe,
            line=line,
        )

    def register_capability(self, capability_id, handler) -> None:
        self.engine.register_capability(
            profile=self.profile,
            capability_id=capability_id,
            handler=handler,
        )
