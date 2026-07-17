"""SealRelationshipResolver -- UMC-001 Stage 5 (Relationship Resolution),
concrete implementation for the Mechanical Seal Factory Pack
(MWO-LTSA-052 WP-001).

Reuses FACTORY.RESOLUTION.relationship_resolver.RelationshipResolver
unmodified. Per MWO-LTSA-052 Sections 3/6: `seal_pump_compatibility` and
`seal_interchange_compatibility` are already FK-resolved at write time and
need no resolver. The one genuine free-text Seal-side relationship is an
interchange candidate named by another seal's `seal_name` (e.g. an
acquisition source naming "Flowserve-210" as a substitute) -- this resolver
resolves `compatible_seal_name` against `seal_registry.seal_name`, returning
the canonical `seal_registry.seal_code`, the same shape
`seal_interchange_compatibility.compatible_seal_code` already requires
(MWO-LTSA-030). `ltsa_pumps.seal_type` resolution remains Pump-owned
(PumpRelationshipResolver, MWO-LTSA-050) and is not duplicated here.

Mirrors PumpRelationshipResolver (MWO-LTSA-050 WP-001) exactly.

Read-only -- never mutates state. `seal_registry` is supplied by the
caller; this module performs no I/O of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.relationship_resolver import (  # noqa: E402
    RelationshipResolution,
    RelationshipResolver,
)

COMPATIBLE_SEAL_NAME_RELATIONSHIP_KEY = "compatible_seal_name"


class SealRelationshipResolver(RelationshipResolver):
    def __init__(self, seal_registry: list[dict[str, Any]] | None = None):
        self.seal_registry = seal_registry or []

    def resolve(
        self,
        object_type: str,
        candidate_relationships: dict[str, Any],
        context: ManufacturingContext,
    ) -> RelationshipResolution:
        resolved: dict[str, str] = {}
        unresolved: list[str] = []

        for key, value in candidate_relationships.items():
            seal_code = (
                self._find_seal_code(value)
                if key == COMPATIBLE_SEAL_NAME_RELATIONSHIP_KEY
                else None
            )

            if seal_code is not None:
                resolved[key] = seal_code
            else:
                unresolved.append(key)

        return RelationshipResolution(resolved=resolved, unresolved=unresolved)

    def _find_seal_code(self, seal_name: Any) -> str | None:
        for seal in self.seal_registry:
            if seal.get("seal_name") == seal_name:
                return seal.get("seal_code")
        return None
