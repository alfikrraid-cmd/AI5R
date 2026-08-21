"""MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- read support for
seal_unit, the canonical PHYSICAL mechanical-seal identity primitive
(distinct from seal_registry, which is the SEAL TYPE / catalog
identity -- never conflated: seal_code identifies a type, seal_unit_id
identifies one physical unit of that type).

This is identity-foundation scope only: create()/list()/find() exist so
the primitive is provable and queryable; no install/remove/repair
action, no status transition, no stock adjustment. `create()` accepts
`status` only because a caller must be able to record which of the 7
identity-safe states (IN_STOCK/INSTALLED/REMOVED/UNDER_INSPECTION/
UNDER_REPAIR/REPAIRED/SCRAPPED) a unit starts in -- it is not a
transition method, and no other method here changes status.

validate_no_seal_code_contradiction() is the one business-rule check
this MWO requires ("if seal_unit_id is supplied on an installation
report, seal_unit.seal_code and installation_report.seal_code must not
contradict") -- enforced at the application layer, not a DB trigger:
this whole codebase has zero triggers anywhere (confirmed by repo-wide
search), and every other cross-table business rule in this schema is
already enforced in Python service/repository code, never SQL trigger
code. A pure function, independently testable, deliberately not wired
into any write endpoint yet (this MWO adds no installation_report write
path -- see this MWO's own "NO install/remove/repair action routes").
"""

from __future__ import annotations

import json
import sys
import uuid as _uuid_module
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

# The 7 identity-safe states this MWO defines. No transition logic here --
# validity of a given value is the only thing this module checks.
SEAL_UNIT_STATUSES = frozenset(
    {"IN_STOCK", "INSTALLED", "REMOVED", "UNDER_INSPECTION", "UNDER_REPAIR", "REPAIRED", "SCRAPPED"}
)

_SELECT_COLUMNS = (
    "seal_unit_id, seal_code, serial_number, status, current_pump_tag_number, created_at, updated_at"
)


def is_valid_uuid(value: str) -> bool:
    """MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- closes the disclosed
    malformed-UUID gap: a non-UUID path parameter must never reach the
    database (Postgres raises a raw InvalidTextRepresentation error for
    `uuid_column = 'not-a-uuid'`, which the router previously let
    propagate as an uncaught 500). Every UUID-keyed lookup in this module
    checks this FIRST and treats "malformed" identically to "not found"
    (same downstream behavior, same discipline auth_service.py's own
    generic login-failure message already uses: never disclose which
    specific way an identifier failed to resolve)."""
    try:
        _uuid_module.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class SealUnitError(ValueError):
    pass


class SealCodeContradictionError(SealUnitError):
    """Raised when an installation_report's seal_code does not match the
    seal_code of the seal_unit it claims to reference. Never raised by
    schema/FK alone (seal_unit_id and seal_code are two independent
    nullable columns on installation_report today) -- this is the
    explicit application-layer check this MWO's own Relational
    Invariants section requires."""


class SealCodeNotFoundError(SealUnitError):
    """Raised when a registration request's seal_code does not exist in
    seal_registry -- checked explicitly so an unknown seal_code fails
    cleanly (404/422) instead of surfacing seal_unit's own FK constraint
    as a raw, uncaught DB error (the same "never let a raw DB error reach
    the caller" discipline every other seal-domain write in this
    codebase already follows)."""


class DuplicateSerialNumberError(SealUnitError):
    """Raised when a registration request's serial_number already exists
    on another seal_unit -- checked explicitly for the same clean-error
    reason SealCodeNotFoundError is, rather than surfacing seal_unit's
    own partial unique index as a raw UniqueViolation. The index itself
    (idx_seal_unit_serial_number_unique) remains the true, race-proof
    backstop; a genuinely concurrent duplicate registration is rejected
    by the database either way -- this guard only makes the common,
    non-concurrent case return a clean, typed error."""


def validate_no_seal_code_contradiction(
    *, seal_unit_seal_code: str, installation_report_seal_code: str | None
) -> None:
    if installation_report_seal_code is not None and installation_report_seal_code != seal_unit_seal_code:
        raise SealCodeContradictionError(
            f"installation_report.seal_code={installation_report_seal_code!r} contradicts "
            f"seal_unit.seal_code={seal_unit_seal_code!r} for the referenced seal_unit_id"
        )


class SealUnitRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create(
        self,
        *,
        seal_code: str,
        serial_number: str | None = None,
        status: str = "IN_STOCK",
        current_pump_tag_number: str | None = None,
    ) -> dict:
        if status not in SEAL_UNIT_STATUSES:
            raise SealUnitError(f"Unknown seal_unit status: {status!r} (must be one of {sorted(SEAL_UNIT_STATUSES)})")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO seal_unit (seal_code, serial_number, status, current_pump_tag_number) VALUES ("
                f"{_sql(seal_code)}, {_sql(serial_number)}, {_sql(status)}, {_sql(current_pump_tag_number)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_by_id(self, seal_unit_id: str) -> dict | None:
        if not is_valid_uuid(seal_unit_id):
            return None
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_seal_code(self, seal_code: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM seal_unit WHERE seal_code = {_sql(seal_code)} ORDER BY created_at",
            self._runner,
        )

    def list_all(self) -> list[dict]:
        return _json_query(f"SELECT {_SELECT_COLUMNS} FROM seal_unit ORDER BY created_at", self._runner)


# MWO-LTSA-PHYSICAL-SEAL-001B -- the canonical registration write path.
# Registration and installation are separate domain actions (this MWO's
# own explicit rule): a registered unit always starts IN_STOCK with
# current_pump_tag_number NULL -- neither is ever caller-supplied here,
# closing off current_pump_tag_number as an implicit installation
# mechanism structurally, not just by convention. No lifecycle event, no
# installation report, no warranty row is written -- this function's own
# INSERT into seal_unit is the entire side effect.
#
# Same guarded-CTE atomic-write pattern apply_lifecycle_event()/
# create_inspection()/create_repair()/create_warranty_assessment()/
# link_installation_report() already established (single compound
# statement -- inherently atomic in Postgres, no BEGIN/COMMIT needed):
# reuses seal_unit's own real column set unchanged (the same table
# SealUnitRepository.create() already targets, not a second persistence
# path), just guarded so an unknown seal_code or a duplicate serial_number
# fails cleanly instead of surfacing a raw FK/unique-constraint DB error.
def register_seal_unit(
    runner: "DatabaseRunner", *, seal_code: str, serial_number: str | None = None
) -> dict:
    serial_guard_sql = "TRUE"
    if serial_number is not None:
        serial_guard_sql = (
            f"NOT EXISTS (SELECT 1 FROM seal_unit WHERE serial_number = {_sql(serial_number)})"
        )

    script = f"""
WITH seal_ok AS (
    SELECT seal_code FROM seal_registry WHERE seal_code = {_sql(seal_code)}
),
serial_ok AS (
    SELECT * FROM seal_ok WHERE {serial_guard_sql}
),
ins AS (
    INSERT INTO seal_unit (seal_code, serial_number, status, current_pump_tag_number)
    SELECT {_sql(seal_code)}, {_sql(serial_number)}, 'IN_STOCK', NULL
    FROM serial_ok
    RETURNING {_SELECT_COLUMNS}
)
SELECT row_to_json(t)::text FROM (
    SELECT
        (SELECT COUNT(*) FROM seal_ok) AS seal_matched,
        (SELECT COUNT(*) FROM serial_ok) AS serial_matched,
        COALESCE((SELECT json_agg(row_to_json(i))::text FROM ins i), '[]') AS unit_json
) t;
"""
    raw = runner.query_scalar(script.strip())
    if not raw:
        raise SealUnitError("Unexpected empty result registering seal unit")
    outcome = json.loads(raw)
    if int(outcome["seal_matched"]) == 0:
        raise SealCodeNotFoundError(seal_code)
    if int(outcome["serial_matched"]) == 0:
        raise DuplicateSerialNumberError(serial_number)
    units = json.loads(outcome["unit_json"])
    if not units:
        raise SealUnitError("Unexpected: guard matched but no seal_unit was inserted")
    return units[0]


__all__ = [
    "SealUnitRepository",
    "SealUnitError",
    "SealCodeContradictionError",
    "SealCodeNotFoundError",
    "DuplicateSerialNumberError",
    "SEAL_UNIT_STATUSES",
    "validate_no_seal_code_contradiction",
    "register_seal_unit",
    "is_valid_uuid",
]
