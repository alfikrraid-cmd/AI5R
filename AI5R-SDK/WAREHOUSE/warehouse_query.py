from typing import Any, List

from WAREHOUSE.warehouse_object import WarehouseObject
from WAREHOUSE.warehouse_registry import WarehouseRegistry


class WarehouseQueryEngine:
    def __init__(self, registry: WarehouseRegistry):
        self.registry = registry

    def all(self) -> List[WarehouseObject]:
        return self.registry.list_all()

    def by_tag(self, tag: str) -> List[WarehouseObject]:
        return [
            obj for obj in self.registry.list_all()
            if tag in obj.tags
        ]

    def by_policy(self, policy_id: str) -> List[WarehouseObject]:
        return [
            obj for obj in self.registry.list_all()
            if policy_id in obj.policy_ids
        ]

    def by_metadata(self, key: str, value: Any) -> List[WarehouseObject]:
        return [
            obj for obj in self.registry.list_all()
            if obj.metadata.get(key) == value
        ]

    def by_payload_field(self, key: str, value: Any) -> List[WarehouseObject]:
        return [
            obj for obj in self.registry.list_all()
            if obj.payload.get(key) == value
        ]
