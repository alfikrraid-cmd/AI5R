from dataclasses import dataclass, field
from typing import Any

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

    def validate(self) -> bool:
        return bool(
            self.factory_id
            and self.factory_name
            and self.profile
        )

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

    def register_capability(self, capability_id, handler) -> None:
        self.engine.register_capability(
            profile=self.profile,
            capability_id=capability_id,
            handler=handler,
        )
