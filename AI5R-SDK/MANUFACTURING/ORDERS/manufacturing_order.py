from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from MANUFACTURING.OBJECTS import (
    ManufacturingObject,
    ManufacturingObjectType,
)


class ManufacturingOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    SCHEDULED = "SCHEDULED"
    IN_PRODUCTION = "IN_PRODUCTION"
    QA_REVIEW = "QA_REVIEW"
    PACKAGED = "PACKAGED"
    DEPLOYED = "DEPLOYED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ManufacturingOrderPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ManufacturingOrder:
    order_id: str
    product_name: str
    product_type: str
    requested_by: str
    recipe_id: str | None = None
    dbom_id: str | None = None
    priority: ManufacturingOrderPriority = ManufacturingOrderPriority.MEDIUM
    status: ManufacturingOrderStatus = ManufacturingOrderStatus.DRAFT
    requirements: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_base: str = "ManufacturingObject"

    def validate(self) -> bool:
        return bool(
            self.order_id
            and self.product_name
            and self.product_type
            and self.requested_by
            and self.canonical_base == "ManufacturingObject"
        )

    def to_manufacturing_object(self) -> ManufacturingObject:
        return ManufacturingObject(
            object_id=self.order_id,
            object_type=ManufacturingObjectType.MANUFACTURING_ORDER,
            name=self.product_name,
            metadata={
                "product_type": self.product_type,
                "requested_by": self.requested_by,
                "recipe_id": self.recipe_id,
                "dbom_id": self.dbom_id,
                "priority": self.priority.value,
                "status": self.status.value,
                "requirements": self.requirements,
                **self.metadata,
            },
        )

    def is_ready_for_planning(self) -> bool:
        return self.validate() and self.status == ManufacturingOrderStatus.DRAFT
