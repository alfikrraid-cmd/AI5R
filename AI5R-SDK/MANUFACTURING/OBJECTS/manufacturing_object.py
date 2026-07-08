from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ManufacturingObjectType(str, Enum):
    FACTORY = "FACTORY"
    RECIPE = "RECIPE"
    DBOM = "DBOM"
    MANUFACTURING_ORDER = "MANUFACTURING_ORDER"
    PRODUCTION_SCHEDULER = "PRODUCTION_SCHEDULER"
    MANUFACTURING_LINE = "MANUFACTURING_LINE"
    MANUFACTURING_STATION = "MANUFACTURING_STATION"
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE"
    PACKAGE = "PACKAGE"
    DEPLOYMENT = "DEPLOYMENT"
    PRODUCT = "PRODUCT"


@dataclass(frozen=True)
class ManufacturingObject:
    object_id: str
    object_type: ManufacturingObjectType
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_base: str = "EnterpriseObject"

    def validate(self) -> bool:
        return bool(
            self.object_id
            and self.object_type
            and self.name
            and self.canonical_base == "EnterpriseObject"
        )

    def is_canonical_reuse(self) -> bool:
        return self.canonical_base == "EnterpriseObject"
