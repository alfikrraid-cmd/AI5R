"""PumpManufacturingStation -- the Pump Factory Pack's manufacturing station
(MWO-LTSA-050 WP-001).

Subclasses FACTORY.CORE.manufacturing_station.BaseManufacturingStation
unmodified, per Chief Architect directive: Manufacturing Station is a
Factory concept (not an ADR-003 Capability), reusing UMC-001's existing
lifecycle rather than introducing a second execution model.

Exposes `.run(payload: dict) -> dict`, the shape
FACTORY.FOUNDATION.manufacturing_pipeline.ManufacturingPipeline actually
calls (UMR-001 Section 5, `ContextReadingStation` precedent) -- distinct
from, and bridging to, the inherited `.manufacture(payload, metadata)`
(UMC-001 Stage 3/6-8, `CORE.BaseManufacturingStation`'s own contract).

Wiring, in UMC-001 stage order:
  Stage 3 (Validation)             -- self.validate() via required_input
  Stage 4 (Identity Resolution)    -- context.metadata["identity_resolver"]
  Stage 5 (Relationship Resolution)-- context.metadata["relationship_resolver"]
  Stage 6-8 (Object/Event/Result)  -- inherited BaseManufacturingStation.manufacture()

Both resolvers are optional (absent -> stage skipped, matching UMR-001's own
"reachable, never invoked by the runtime itself" contract) so this station
also runs standalone, outside a full ManufacturingContext, for direct
testing. A pump whose tag_number already resolves (Stage 4 `matched=True`)
is a duplicate, not a new canonical object -- rejected before Stage 6 with
status "PUMP_ALREADY_EXISTS" rather than manufactured again.
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

PUMP_OBJECT_TYPE = "PUMP"


class PumpManufacturingStation(BaseManufacturingStation):
    station_code = "MF-PUMP"
    station_name = "Pump Manufacturing Station"
    object_type = PUMP_OBJECT_TYPE
    event_type = "PUMP_MANUFACTURED"
    required_input = "tag_number"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context")
        pump = payload.get("definition", {}).get("pump", {})

        self.validate(pump)

        identity_resolution = self._resolve_identity(pump, context)

        if identity_resolution is not None and identity_resolution.matched:
            payload["status"] = "PUMP_ALREADY_EXISTS"
            payload["identity_resolution"] = asdict(identity_resolution)
            return payload

        relationship_resolution = self._resolve_relationships(pump, context)

        result = self.manufacture(
            pump,
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
        payload["pump_events"] = result.events
        return payload

    def _resolve_identity(self, pump: dict[str, Any], context):
        if context is None:
            return None

        identity_resolver = context.metadata.get("identity_resolver")
        if identity_resolver is None:
            return None

        return identity_resolver.resolve(
            self.object_type, {"tag_number": pump.get("tag_number")}, context
        )

    def _resolve_relationships(self, pump: dict[str, Any], context):
        if context is None:
            return None

        relationship_resolver = context.metadata.get("relationship_resolver")
        if relationship_resolver is None:
            return None

        return relationship_resolver.resolve(
            self.object_type, {"seal_type": pump.get("seal_type")}, context
        )
