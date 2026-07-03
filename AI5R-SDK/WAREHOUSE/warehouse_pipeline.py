from typing import Any, Dict, List, Optional

from WAREHOUSE.warehouse_registry import WarehouseRegistry
from WAREHOUSE.warehouse_ingestion import WarehouseIngestionEngine
from WAREHOUSE.warehouse_validation import WarehouseValidationEngine
from WAREHOUSE.warehouse_object import WarehouseObject


class WarehousePipeline:
    def __init__(self):
        self.registry = WarehouseRegistry()
        self.ingestion = WarehouseIngestionEngine(self.registry)
        self.validator = WarehouseValidationEngine()

    def process(
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
        obj = self.ingestion.ingest(
            source_type=source_type,
            source_id=source_id,
            object_type=object_type,
            payload=payload,
            organization_id=organization_id,
            owner_worker_id=owner_worker_id,
            tags=tags,
            metadata=metadata,
            policy_ids=policy_ids,
        )

        if not self.validator.validate(obj):
            raise ValueError(self.validator.errors(obj))

        return obj

    def list_all(self) -> List[WarehouseObject]:
        return self.registry.list_all()
