from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from MANUFACTURING.OBJECTS import (
    ManufacturingObject,
    ManufacturingObjectType,
)


class DBOMComponentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    PLANNED = "PLANNED"
    DEPRECATED = "DEPRECATED"


class DBOMComponentType(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DATABASE = "DATABASE"
    API = "API"
    AUTH = "AUTH"
    UI = "UI"
    KNOWLEDGE = "KNOWLEDGE"
    PROMPT = "PROMPT"
    MEMORY = "MEMORY"
    TOOL = "TOOL"
    WORKFLOW = "WORKFLOW"
    DOCUMENT = "DOCUMENT"
    DASHBOARD = "DASHBOARD"
    TEST = "TEST"
    DEPLOYMENT = "DEPLOYMENT"
    CONTENT = "CONTENT"
    MEDIA = "MEDIA"
    POLICY = "POLICY"


@dataclass(frozen=True)
class DBOMComponent:
    component_id: str
    name: str
    component_type: DBOMComponentType
    status: DBOMComponentStatus = DBOMComponentStatus.PLANNED
    reusable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        return bool(
            self.component_id
            and self.name
            and self.component_type
            and self.status
        )


@dataclass(frozen=True)
class DigitalBillOfMaterials:
    dbom_id: str
    product_type: str
    components: tuple[DBOMComponent, ...]
    version: str = "1.0.0"
    canonical_base: str = "ManufacturingObject"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        if not self.dbom_id:
            return False
        if not self.product_type:
            return False
        if not self.components:
            return False
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            return False
        return all(component.validate() for component in self.components)

    def missing_components(self) -> list[DBOMComponent]:
        return [
            component
            for component in self.components
            if component.status == DBOMComponentStatus.MISSING
        ]

    def available_components(self) -> list[DBOMComponent]:
        return [
            component
            for component in self.components
            if component.status == DBOMComponentStatus.AVAILABLE
        ]

    def reusable_components(self) -> list[DBOMComponent]:
        return [
            component
            for component in self.components
            if component.reusable
        ]

    def is_ready_for_manufacturing(self) -> bool:
        return self.validate() and not self.missing_components()

    def to_manufacturing_object(self) -> ManufacturingObject:
        return ManufacturingObject(
            object_id=self.dbom_id,
            object_type=ManufacturingObjectType.DBOM,
            name=f"{self.product_type} DBOM",
            metadata={
                "product_type": self.product_type,
                "version": self.version,
                "component_count": len(self.components),
                "missing_component_count": len(self.missing_components()),
                **self.metadata,
            },
        )
