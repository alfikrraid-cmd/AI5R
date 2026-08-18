"""MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- manual completion of
seal_registry's KIMAP Pertamina / GPN John Crane identifiers.

Direct-Postgres, not a SealGateway/n8n write: SealGateway is deliberately
read-only (its own test_gateway_has_no_write_methods asserts this,
disclosed there as scoped to Inventory Context's read needs, "growing
write methods later" explicitly deferred to "a matching MWO" -- this one).
The existing n8n WF-LTSA-BRAIN-SEAL-UPDATE-001 workflow's own field
allowlist (seal_name/manufacturer/model/shaft_size/material/
temperature_limit/pressure_limit/status) does not include the two new
identifier columns or updated_by attribution, and editing/proving an n8n
workflow JSON has no equivalent to this codebase's disposable-Postgres
verification path. Reusing the exact DatabaseRunner/_json_query/_sql
machinery auth_repository.py already established for a narrow,
provably-testable admin-style write is the smaller, safer, evidence-
grounded choice here -- not a second SQL layer, the same one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


def normalize_identifier_field(value: str | None) -> str | None:
    """Empty-string/None equivalence (Phase 17: "empty-string vs NULL
    semantics must be explicit"): a manual field is either a real,
    non-blank value or NULL -- an empty string is never persisted, since
    "the operator cleared this field" and "no value was ever entered"
    are the same fact for KIMAP/GPN. Whitespace-only input is treated the
    same way (stripped first, then checked)."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class SealMasterDataRepository:
    """Reads/writes only the four columns migration 013 added
    (kimap_pertamina, gpn_john_crane, created_by, updated_by) -- every
    other seal_registry column remains ingestion-owned and untouched by
    this repository, matching Hard Rule 5/Phase 5's "do not make every
    column editable" instruction."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_seal_identifiers(self, seal_code: str) -> dict | None:
        rows = _json_query(
            "SELECT seal_code, kimap_pertamina, gpn_john_crane, "
            "created_by, updated_by, created_at, updated_at "
            f"FROM seal_registry WHERE seal_code = {_sql(seal_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def update_seal_identifiers(
        self,
        seal_code: str,
        *,
        kimap_pertamina: str | None,
        gpn_john_crane: str | None,
        updated_by: str,
    ) -> dict | None:
        """Sets both identifier fields together (the caller always submits
        the full desired identifier state, not a sparse patch -- Phase 17
        chose this over unset-vs-null pydantic detection as the smallest
        correct contract for a two-field form). created_by is
        DELIBERATELY never referenced here -- Hard Rule 10/11: the
        creator, once set (or left NULL for imported rows -- Phase 7's
        "do not fabricate a human creator for legacy data"), is never
        touched by an update. Returns None if seal_code does not exist
        (router maps this to 404); quantity_on_hand/seal_stock is never
        referenced by this query at all -- Phase 10's "stock quantity
        cannot be edited through this API" is structural, not a check."""
        # _json_query's own `FROM (sql) t` wrapping only works for a plain
        # SELECT (an UPDATE cannot appear as a FROM subquery) -- the same
        # issue auth_repository.create_user already hit and fixed with a
        # real CTE; this is that identical, proven shape, not a fresh
        # pattern.
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE seal_registry SET "
                f"kimap_pertamina = {_sql(kimap_pertamina)}, "
                f"gpn_john_crane = {_sql(gpn_john_crane)}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE seal_code = {_sql(seal_code)} "
                "RETURNING seal_code, kimap_pertamina, gpn_john_crane, "
                "created_by, updated_by, created_at, updated_at"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None


__all__ = ["SealMasterDataRepository", "normalize_identifier_field"]
