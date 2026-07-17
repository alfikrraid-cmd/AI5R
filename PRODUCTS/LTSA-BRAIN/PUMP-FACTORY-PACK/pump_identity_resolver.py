"""PumpIdentityResolver -- UMC-001 Stage 4 (Identity Resolution), concrete
implementation for the Pump Factory Pack (MWO-LTSA-050 WP-001).

Reuses FACTORY.RESOLUTION.identity_resolver.IdentityResolver unmodified.
Resolves a candidate pump by its natural key, `tag_number`, against
`ltsa_pumps` (PRODUCTS/LTSA-BRAIN/MODULES/PUMP/DATABASE/001_create_pumps.sql)
-- confirmed canonical, `tag_number` confirmed as the natural key by its own
`UNIQUE NOT NULL` constraint and by `seal_pump_compatibility`'s existing FK.

Read-only -- never mutates state. `known_pumps` is supplied by the caller
(e.g. a query result); this module performs no I/O of its own, consistent
with every other FACTORY.RESOLUTION concrete class.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_AI5R_SDK_PATH = Path(__file__).resolve().parents[2] / "AI5R-SDK"
if str(_AI5R_SDK_PATH) not in sys.path:
    sys.path.insert(0, str(_AI5R_SDK_PATH))

from FACTORY.FOUNDATION.manufacturing_context import ManufacturingContext  # noqa: E402
from FACTORY.RESOLUTION.identity_resolver import IdentityResolution, IdentityResolver  # noqa: E402

PUMP_OBJECT_TYPE = "PUMP"


class PumpIdentityResolver(IdentityResolver):
    def __init__(self, known_pumps: list[dict[str, Any]] | None = None):
        self.known_pumps = known_pumps or []

    def resolve(
        self,
        object_type: str,
        candidate_key: dict[str, Any],
        context: ManufacturingContext,
    ) -> IdentityResolution:
        if object_type != PUMP_OBJECT_TYPE:
            raise ValueError(
                f"PumpIdentityResolver cannot resolve object_type={object_type!r}"
            )

        tag_number = candidate_key.get("tag_number")

        for pump in self.known_pumps:
            if pump.get("tag_number") == tag_number:
                return IdentityResolution(
                    matched=True,
                    canonical_id=pump.get("id") or tag_number,
                    confidence=1.0,
                )

        return IdentityResolution(matched=False, canonical_id=None, confidence=None)
