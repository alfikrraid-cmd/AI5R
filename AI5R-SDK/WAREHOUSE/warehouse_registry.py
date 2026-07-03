from typing import Dict, List, Optional

from WAREHOUSE.warehouse_object import WarehouseObject


class WarehouseRegistry:
    def __init__(self):
        self.objects: Dict[str, WarehouseObject] = {}

    def register(self, obj: WarehouseObject) -> WarehouseObject:
        if not obj.is_valid():
            raise ValueError("Invalid WarehouseObject")

        self.objects[obj.id] = obj
        return obj

    def get(self, object_id: str) -> Optional[WarehouseObject]:
        return self.objects.get(object_id)

    def list_all(self) -> List[WarehouseObject]:
        return list(self.objects.values())

    def find_by_source(self, source_type: str, source_id: str) -> List[WarehouseObject]:
        return [
            obj for obj in self.objects.values()
            if obj.source_type == source_type and obj.source_id == source_id
        ]

    def find_by_object_type(self, object_type: str) -> List[WarehouseObject]:
        return [
            obj for obj in self.objects.values()
            if obj.object_type == object_type
        ]
