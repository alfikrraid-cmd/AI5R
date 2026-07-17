"""SealManufacturingStation -- the Mechanical Seal Factory Pack's
manufacturing station (MWO-LTSA-052 WP-001).

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
testing. A seal whose seal_code already resolves (Stage 4 `matched=True`)
is a duplicate, not a new canonical object -- rejected before Stage 6 with
status "SEAL_ALREADY_EXISTS" rather than manufactured again.

Mirrors PumpManufacturingStation (MWO-LTSA-050 WP-001) exactly.
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

SEAL_OBJECT_TYPE = "SEAL"


class SealManufacturingStation(BaseManufacturingStation):
    station_code = "MF-SEAL"
    station_name = "Mechanical Seal Manufacturing Station"
    object_type = SEAL_OBJECT_TYPE
    event_type = "SEAL_MANUFACTURED"
    required_input = "seal_code"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context")
        seal = payload.get("definition", {}).get("seal", {})

        self.validate(seal)

        identity_resolution = self._resolve_identity(seal, context)

        if identity_resolution is not None and identity_resolution.matched:
            payload["status"] = "SEAL_ALREADY_EXISTS"
            payload["identity_resolution"] = asdict(identity_resolution)
            return payload

        relationship_resolution = self._resolve_relationships(seal, context)

        result = self.manufacture(
            seal,
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
        payload["seal_events"] = result.events
        return payload

    def _resolve_identity(self, seal: dict[str, Any], context):
        if context is None:
            return None

        identity_resolver = context.metadata.get("identity_resolver")
        if identity_resolver is None:
            return None

        return identity_resolver.resolve(
            self.object_type, {"seal_code": seal.get("seal_code")}, context
        )

    def _resolve_relationships(self, seal: dict[str, Any], context):
        if context is None:
            return None

        relationship_resolver = context.metadata.get("relationship_resolver")
        if relationship_resolver is None:
            return None

        return relationship_resolver.resolve(
            self.object_type,
            {"compatible_seal_name": seal.get("compatible_seal_name")},
            context,
        )
