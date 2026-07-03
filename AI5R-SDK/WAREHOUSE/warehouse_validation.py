from typing import List

from WAREHOUSE.warehouse_object import WarehouseObject


class WarehouseValidationEngine:
    def validate(self, obj: WarehouseObject) -> bool:
        return obj.is_valid() and bool(obj.payload)

    def validate_batch(self, objects: List[WarehouseObject]) -> bool:
        return all(self.validate(obj) for obj in objects)

    def errors(self, obj: WarehouseObject) -> List[str]:
        errors = []

        if not obj.id:
            errors.append("Missing id")
        if not obj.code:
            errors.append("Missing code")
        if not obj.source_type:
            errors.append("Missing source_type")
        if not obj.source_id:
            errors.append("Missing source_id")
        if not obj.object_type:
            errors.append("Missing object_type")
        if not isinstance(obj.payload, dict):
            errors.append("Payload must be dict")
        if isinstance(obj.payload, dict) and not obj.payload:
            errors.append("Payload is empty")

        return errors
