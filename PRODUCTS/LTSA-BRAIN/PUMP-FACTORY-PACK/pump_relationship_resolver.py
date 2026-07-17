"""PumpRelationshipResolver -- UMC-001 Stage 5 (Relationship Resolution),
concrete implementation for the Pump Factory Pack (MWO-LTSA-050 WP-001).

Reuses FACTORY.RESOLUTION.relationship_resolver.RelationshipResolver
unmodified. Resolves a pump's free-text `seal_type`
(PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql --
`ltsa_pumps.seal_type`, not an FK) against `seal_registry.seal_name`,
returning the canonical `seal_registry.seal_code` -- the same cross-
reference already load-bearing via `seal_pump_compatibility`
(BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY, MWO-LTSA-030).

`seal_type` is the only relationship key this resolver knows how to
resolve; any other candidate key is reported unresolved, not guessed at.

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

SEAL_TYPE_RELATIONSHIP_KEY = "seal_type"


class PumpRelationshipResolver(RelationshipResolver):
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
                self._find_seal_code(value) if key == SEAL_TYPE_RELATIONSHIP_KEY else None
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
