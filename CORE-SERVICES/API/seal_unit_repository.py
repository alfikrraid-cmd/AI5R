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


class SealUnitError(ValueError):
    pass


class SealCodeContradictionError(SealUnitError):
    """Raised when an installation_report's seal_code does not match the
    seal_code of the seal_unit it claims to reference. Never raised by
    schema/FK alone (seal_unit_id and seal_code are two independent
    nullable columns on installation_report today) -- this is the
    explicit application-layer check this MWO's own Relational
    Invariants section requires."""


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


__all__ = [
    "SealUnitRepository",
    "SealUnitError",
    "SealCodeContradictionError",
    "SEAL_UNIT_STATUSES",
    "validate_no_seal_code_contradiction",
]
