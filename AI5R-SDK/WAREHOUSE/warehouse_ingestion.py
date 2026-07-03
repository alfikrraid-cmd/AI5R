from typing import Any, Dict, List, Optional
from uuid import uuid4

from WAREHOUSE.warehouse_object import WarehouseObject
from WAREHOUSE.warehouse_registry import WarehouseRegistry


class WarehouseIngestionEngine:
    def __init__(self, registry: WarehouseRegistry):
        self.registry = registry

    def ingest(
        self,
        source_type: str,
        source_id: str,
        object_type: str,
        payload: Dict[str, Any],
        organization_id: Optional[str] = None,
        owner_worker_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        policy_ids: Optional[List[str]] = None,
    ) -> WarehouseObject:
        obj = WarehouseObject(
            id=str(uuid4()),
            code=f"WH-{source_type.upper()}-{source_id}",
            source_type=source_type,
            source_id=source_id,
            object_type=object_type,
            payload=payload,
            organization_id=organization_id,
            owner_worker_id=owner_worker_id,
            tags=tags or [],
            metadata=metadata or {},
            policy_ids=policy_ids or [],
        )

        return self.registry.register(obj)
