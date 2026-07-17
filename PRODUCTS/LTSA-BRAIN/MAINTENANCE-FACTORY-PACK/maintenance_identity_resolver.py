"""MaintenanceIdentityResolver -- UMC-001 Stage 4 (Identity Resolution),
concrete implementation for the Maintenance Factory Pack (MWO-LTSA-054
WP-001).

Reuses FACTORY.RESOLUTION.identity_resolver.IdentityResolver unmodified.
Per MWO-LTSA-054 WP-000 Finding 1, Maintenance is two canonical objects, not
one: Work Order (`public.work_order`, natural key `work_order_code`) and
Maintenance History (`public.maintenance_history`, natural key
`maintenance_record_code`) -- both PRIMARY KEY TEXT columns, confirmed in
`PRODUCTS/LTSA-BRAIN/DATABASE/CANONICAL_SCHEMA.sql`. One resolver class,
parameterized by object_type, matching the "one resolver instance
parameterized by object_type" option WP-000's own Factory Pack Boundaries
table left open -- selected here because Chief Direction requested exactly
one `maintenance_identity_resolver.py` file, not two.

Read-only -- never mutates state. Reference data is supplied by the caller;
this module performs no I/O of its own, consistent with every other
FACTORY.RESOLUTION concrete class (PumpIdentityResolver, SealIdentityResolver).
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

WORK_ORDER_OBJECT_TYPE = "WORK_ORDER"
MAINTENANCE_RECORD_OBJECT_TYPE = "MAINTENANCE_RECORD"

_IDENTITY_FIELD = {
    WORK_ORDER_OBJECT_TYPE: "work_order_code",
    MAINTENANCE_RECORD_OBJECT_TYPE: "maintenance_record_code",
}


class MaintenanceIdentityResolver(IdentityResolver):
    def __init__(
        self,
        known_work_orders: list[dict[str, Any]] | None = None,
        known_maintenance_records: list[dict[str, Any]] | None = None,
    ):
        self.known_work_orders = known_work_orders or []
        self.known_maintenance_records = known_maintenance_records or []

    def resolve(
        self,
        object_type: str,
        candidate_key: dict[str, Any],
        context: ManufacturingContext,
    ) -> IdentityResolution:
        if object_type not in _IDENTITY_FIELD:
            raise ValueError(
                f"MaintenanceIdentityResolver cannot resolve object_type={object_type!r}"
            )

        identity_field = _IDENTITY_FIELD[object_type]
        known_records = (
            self.known_work_orders
            if object_type == WORK_ORDER_OBJECT_TYPE
            else self.known_maintenance_records
        )
        candidate_value = candidate_key.get(identity_field)

        for record in known_records:
            if record.get(identity_field) == candidate_value:
                return IdentityResolution(
                    matched=True,
                    canonical_id=candidate_value,
                    confidence=1.0,
                )

        return IdentityResolution(matched=False, canonical_id=None, confidence=None)
