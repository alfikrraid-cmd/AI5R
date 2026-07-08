from dataclasses import dataclass, field
from typing import Any


@dataclass
class FactoryPack:
    pack_code: str
    pack_name: str
    product_type: str
    capabilities: list[str]
    recipe_path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        if not self.pack_code:
            raise ValueError("pack_code is required")

        if not self.pack_name:
            raise ValueError("pack_name is required")

        if not self.product_type:
            raise ValueError("product_type is required")

        if not self.capabilities:
            raise ValueError("capabilities are required")

        if not self.recipe_path:
            raise ValueError("recipe_path is required")

        return True
