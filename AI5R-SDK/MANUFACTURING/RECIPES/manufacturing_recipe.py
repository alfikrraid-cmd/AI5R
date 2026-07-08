from dataclasses import dataclass, field
from typing import Any

from MANUFACTURING.OBJECTS import (
    ManufacturingObject,
    ManufacturingObjectType,
)


@dataclass(frozen=True)
class ManufacturingRecipe:
    recipe_id: str
    recipe_name: str
    product_type: str

    dbom_id: str
    production_line_id: str

    qa_policy_id: str

    packaging_id: str

    deployment_id: str

    version: str = "1.0.0"

    metadata: dict[str, Any] = field(default_factory=dict)

    canonical_base: str = "ManufacturingObject"

    def validate(self) -> bool:
        return bool(
            self.recipe_id
            and self.recipe_name
            and self.product_type
            and self.dbom_id
            and self.production_line_id
            and self.qa_policy_id
            and self.packaging_id
            and self.deployment_id
            and self.canonical_base == "ManufacturingObject"
        )

    def to_manufacturing_object(self) -> ManufacturingObject:
        return ManufacturingObject(
            object_id=self.recipe_id,
            object_type=ManufacturingObjectType.RECIPE,
            name=self.recipe_name,
            metadata={
                "product_type": self.product_type,
                "dbom_id": self.dbom_id,
                "production_line_id": self.production_line_id,
                "qa_policy_id": self.qa_policy_id,
                "packaging_id": self.packaging_id,
                "deployment_id": self.deployment_id,
                "version": self.version,
                **self.metadata,
            },
        )

    def is_ready(self) -> bool:
        return self.validate()
