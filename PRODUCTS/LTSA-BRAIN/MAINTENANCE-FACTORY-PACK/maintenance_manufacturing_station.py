"""MaintenanceManufacturingStation -- the Maintenance Factory Pack's
manufacturing station (MWO-LTSA-054 WP-001).

Subclasses FACTORY.CORE.manufacturing_station.BaseManufacturingStation
unmodified, same Chief Architect directive as PumpManufacturingStation /
SealManufacturingStation: Manufacturing Station is a Factory concept, not an
ADR-003 Capability.

Per MWO-LTSA-054 WP-000 Finding 1, Maintenance is two canonical objects
(Work Order, Maintenance History), and Chief Direction requested exactly one
`maintenance_manufacturing_station.py` file -- so this station dispatches on
`payload["definition"]["object_type"]` (`"WORK_ORDER"` or
`"MAINTENANCE_RECORD"`), setting `self.object_type`/`self.event_type`/
`self.required_input` per call before delegating to the inherited,
unmodified `self.validate()`/`self.manufacture()` -- no new execution model,
same Stage 3-8 wiring PumpManufacturingStation/SealManufacturingStation use.

Wiring, in UMC-001 stage order:
  Stage 3 (Validation)             -- self.validate() via required_input
  Stage 4 (Identity Resolution)    -- context.metadata["identity_resolver"]
  Stage 5 (Relationship Resolution)-- context.metadata["relationship_resolver"]
  Stage 6-8 (Object/Event/Result)  -- inherited BaseManufacturingStation.manufacture()

Both resolvers are optional (absent -> stage skipped). A record whose
identity already resolves is a duplicate, not a new canonical object --
rejected before Stage 6 with a per-object-type "_ALREADY_EXISTS" status.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.CORE.manufacturing_station import BaseManufacturingStation  # noqa: E402

WORK_ORDER_OBJECT_TYPE = "WORK_ORDER"
MAINTENANCE_RECORD_OBJECT_TYPE = "MAINTENANCE_RECORD"

_OBJECT_CONFIG = {
    WORK_ORDER_OBJECT_TYPE: {
        "definition_key": "work_order",
        "identity_field": "work_order_code",
        "required_input": "work_order_code",
        "event_type": "WORK_ORDER_MANUFACTURED",
        "already_exists_status": "WORK_ORDER_ALREADY_EXISTS",
    },
    MAINTENANCE_RECORD_OBJECT_TYPE: {
        "definition_key": "maintenance_record",
        "identity_field": "maintenance_record_code",
        "required_input": "maintenance_record_code",
        "event_type": "MAINTENANCE_RECORD_MANUFACTURED",
        "already_exists_status": "MAINTENANCE_RECORD_ALREADY_EXISTS",
    },
}


class MaintenanceManufacturingStation(BaseManufacturingStation):
    station_code = "MF-MAINTENANCE"
    station_name = "Maintenance Manufacturing Station"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context")
        definition = payload.get("definition", {})
        object_type = definition.get("object_type")

        config = _OBJECT_CONFIG.get(object_type)
        if config is None:
            raise ValueError(
                f"MaintenanceManufacturingStation cannot manufacture object_type={object_type!r}"
            )

        self.object_type = object_type
        self.event_type = config["event_type"]
        self.required_input = config["required_input"]

        record = definition.get(config["definition_key"], {})

        self.validate(record)

        identity_resolution = self._resolve_identity(object_type, config, record, context)

        if identity_resolution is not None and identity_resolution.matched:
            payload["status"] = config["already_exists_status"]
            payload["identity_resolution"] = asdict(identity_resolution)
            return payload

        relationship_resolution = self._resolve_relationships(object_type, record, context)

        result = self.manufacture(
            record,
            metadata={
                "identity_resolution": (
                    asdict(identity_resolution) if identity_resolution is not None else None
                ),
                "relationship_resolution": (
                    asdict(relationship_resolution)
                    if relationship_resolution is not None
                    else None
                ),
            },
        )

        payload["status"] = result.status
        payload["manufactured_object"] = result.manufactured_object
        payload["object_id"] = result.object_id
        payload["maintenance_events"] = result.events
        return payload

    def _resolve_identity(
        self, object_type: str, config: dict[str, Any], record: dict[str, Any], context
    ):
        if context is None:
            return None

        identity_resolver = context.metadata.get("identity_resolver")
        if identity_resolver is None:
            return None

        identity_field = config["identity_field"]
        return identity_resolver.resolve(
            object_type, {identity_field: record.get(identity_field)}, context
        )

    def _resolve_relationships(self, object_type: str, record: dict[str, Any], context):
        if context is None:
            return None

        relationship_resolver = context.metadata.get("relationship_resolver")
        if relationship_resolver is None:
            return None

        candidate_relationships: dict[str, Any] = {}

        if record.get("asset_code") is not None:
            candidate_relationships["asset_code"] = record.get("asset_code")
            candidate_relationships["asset_type"] = record.get("asset_type")

        if object_type == MAINTENANCE_RECORD_OBJECT_TYPE and record.get("work_order_code") is not None:
            candidate_relationships["work_order_code"] = record.get("work_order_code")

        return relationship_resolver.resolve(object_type, candidate_relationships, context)
