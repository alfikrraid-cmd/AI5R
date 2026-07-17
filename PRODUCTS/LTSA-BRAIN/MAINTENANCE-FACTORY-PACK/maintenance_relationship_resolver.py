"""MaintenanceRelationshipResolver -- UMC-001 Stage 5 (Relationship
Resolution), concrete implementation for the Maintenance Factory Pack
(MWO-LTSA-054 WP-001).

Reuses FACTORY.RESOLUTION.relationship_resolver.RelationshipResolver
unmodified. Per MWO-LTSA-054 WP-000 §3, Maintenance has two relationships:

1. `asset_code`/`asset_type` -- a polymorphic reference: an asset may live in
   `ltsa_pumps` (asset_type PUMP), `seal_registry` (SEAL), `asset_registry`
   (ASSET), or `soot_blower_registry` (SOOT_BLOWER) -- four registries with
   no common supertype, exactly as `work_order`/`maintenance_history`'s own
   SQL header comments describe. `asset_type` selects which registry
   `asset_code` is looked up against; this is why this resolver reads two
   candidate keys together rather than one key per call, unlike
   PumpRelationshipResolver/SealRelationshipResolver's single-key shape.
2. `work_order_code` (Maintenance History only) -- deliberately optional
   (`maintenance_history`'s own header comment: kept non-FK "to keep this
   table independently queryable even if a work order record is absent").
   An unresolved result here is a legitimate outcome, not an error --
   `RelationshipResolution(unresolved=[...])` already accommodates this.

Read-only -- never mutates state. Reference data is supplied by the caller;
this module performs no I/O of its own.
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

ASSET_CODE_RELATIONSHIP_KEY = "asset_code"
ASSET_TYPE_KEY = "asset_type"
WORK_ORDER_CODE_RELATIONSHIP_KEY = "work_order_code"

_ASSET_TYPE_REGISTRY = {
    "PUMP": ("known_pumps", "tag_number"),
    "SEAL": ("known_seals", "seal_code"),
    "ASSET": ("known_assets", "asset_code"),
    "SOOT_BLOWER": ("known_soot_blowers", "soot_blower_code"),
}


class MaintenanceRelationshipResolver(RelationshipResolver):
    def __init__(
        self,
        known_pumps: list[dict[str, Any]] | None = None,
        known_seals: list[dict[str, Any]] | None = None,
        known_assets: list[dict[str, Any]] | None = None,
        known_soot_blowers: list[dict[str, Any]] | None = None,
        known_work_orders: list[dict[str, Any]] | None = None,
    ):
        self.known_pumps = known_pumps or []
        self.known_seals = known_seals or []
        self.known_assets = known_assets or []
        self.known_soot_blowers = known_soot_blowers or []
        self.known_work_orders = known_work_orders or []

    def resolve(
        self,
        object_type: str,
        candidate_relationships: dict[str, Any],
        context: ManufacturingContext,
    ) -> RelationshipResolution:
        resolved: dict[str, str] = {}
        unresolved: list[str] = []

        if ASSET_CODE_RELATIONSHIP_KEY in candidate_relationships:
            asset_code = candidate_relationships[ASSET_CODE_RELATIONSHIP_KEY]
            asset_type = candidate_relationships.get(ASSET_TYPE_KEY)

            if self._asset_exists(asset_code, asset_type):
                resolved[ASSET_CODE_RELATIONSHIP_KEY] = asset_code
            else:
                unresolved.append(ASSET_CODE_RELATIONSHIP_KEY)

        if WORK_ORDER_CODE_RELATIONSHIP_KEY in candidate_relationships:
            work_order_code = candidate_relationships[WORK_ORDER_CODE_RELATIONSHIP_KEY]

            if any(
                wo.get("work_order_code") == work_order_code for wo in self.known_work_orders
            ):
                resolved[WORK_ORDER_CODE_RELATIONSHIP_KEY] = work_order_code
            else:
                unresolved.append(WORK_ORDER_CODE_RELATIONSHIP_KEY)

        return RelationshipResolution(resolved=resolved, unresolved=unresolved)

    def _asset_exists(self, asset_code: Any, asset_type: Any) -> bool:
        registry_attr, field = _ASSET_TYPE_REGISTRY.get(asset_type, (None, None))
        if registry_attr is None:
            return False

        registry = getattr(self, registry_attr)
        return any(row.get(field) == asset_code for row in registry)
