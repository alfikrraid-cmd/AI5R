from typing import Dict, List, Any

from WAREHOUSE.warehouse_object import WarehouseObject


class WarehouseExportContract:
    def export_object(self, obj: WarehouseObject) -> Dict[str, Any]:
        return {
            "warehouse_id": obj.id,
            "code": obj.code,
            "source": {
                "type": obj.source_type,
                "id": obj.source_id,
            },
            "object_type": obj.object_type,
            "payload": obj.payload,
            "context": {
                "organization_id": obj.organization_id,
                "owner_worker_id": obj.owner_worker_id,
                "thread_id": obj.thread_id,
                "policy_ids": obj.policy_ids,
                "tags": obj.tags,
            },
            "timestamps": {
                "reality_timestamp": obj.reality_timestamp,
                "warehouse_timestamp": obj.warehouse_timestamp,
            },
            "metadata": obj.metadata,
            "checksum": obj.checksum,
            "version": obj.version,
            "status": obj.status,
        }

    def export_batch(self, objects: List[WarehouseObject]) -> List[Dict[str, Any]]:
        return [self.export_object(obj) for obj in objects]
