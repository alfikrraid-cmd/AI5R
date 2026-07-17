"""SealIdentityResolver -- UMC-001 Stage 4 (Identity Resolution), concrete
implementation for the Mechanical Seal Factory Pack (MWO-LTSA-052 WP-001).

Reuses FACTORY.RESOLUTION.identity_resolver.IdentityResolver unmodified.
Resolves a candidate seal by its natural key, `seal_code`, against
`seal_registry` (PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL/DATABASE/001_create_table.sql)
-- confirmed canonical, `seal_code` confirmed as the natural key by its own
PRIMARY KEY constraint (MWO-LTSA-052 Section 2) -- simpler than Pump's
tag_number/id split, since seal_code is both the surrogate and natural key.

Mirrors PumpIdentityResolver (MWO-LTSA-050 WP-001) exactly.

Read-only -- never mutates state. `known_seals` is supplied by the caller
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

SEAL_OBJECT_TYPE = "SEAL"


class SealIdentityResolver(IdentityResolver):
    def __init__(self, known_seals: list[dict[str, Any]] | None = None):
        self.known_seals = known_seals or []

    def resolve(
        self,
        object_type: str,
        candidate_key: dict[str, Any],
        context: ManufacturingContext,
    ) -> IdentityResolution:
        if object_type != SEAL_OBJECT_TYPE:
            raise ValueError(
                f"SealIdentityResolver cannot resolve object_type={object_type!r}"
            )

        seal_code = candidate_key.get("seal_code")

        for seal in self.known_seals:
            if seal.get("seal_code") == seal_code:
                return IdentityResolution(
                    matched=True,
                    canonical_id=seal_code,
                    confidence=1.0,
                )

        return IdentityResolution(matched=False, canonical_id=None, confidence=None)
