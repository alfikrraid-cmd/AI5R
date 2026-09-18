"""MWO-LTSA-REPORTING-R4 -- real Postgres persistence for ltsa_finding
(migration 037, Reporting R3 schema). Direct-Postgres, same style as
ConditionMonitoringReadingRepository/PMOccurrenceRepository (CTE-shaped
INSERT/UPDATE...RETURNING + a record_change_history audit row in the
same statement) -- no parallel repository framework introduced.

source_record_code is an informal polymorphic reference (no DB FK, same
convention pm_cm_evidence.record_code already established) -- this
repository is the ONLY place that validates it, since the database
itself cannot. _SOURCE_DOMAIN_MAP is the single source of truth for
"which table/column does this source_domain mean" -- never guessed,
never duplicated elsewhere.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class InvalidSourceDomain(Exception):
    """source_domain is not one of the 3 values migration 037's own CHECK
    constraint allows. Raised here (not left to the DB) so the router can
    return a clean 400 instead of a raw constraint-violation 500."""


class SourceRecordNotFound(Exception):
    """source_record_code does not exist in the table source_domain maps
    to. Since source_record_code has no DB FK (polymorphic across 3
    tables), this application-layer check is the ONLY existence guard --
    documented in this repository's own module docstring."""


class AssetMismatch(Exception):
    """Caller supplied an asset_code that disagrees with the source
    transaction's own canonical asset. Never silently overridden or
    silently accepted -- Chief's own R4 Section 5 instruction."""


class ClosedRequiresClosedDate(Exception):
    """status=CLOSED with no closed_date (neither supplied in this call
    nor already present on the row). No stronger existing convention was
    found for this table, so this is the smallest new rule -- never
    auto-filled with today's date (that would be closure inference,
    forbidden by Chief's own R4 Section 6)."""


# domain -> (table, primary_key_column, canonical_asset_column, extra_where)
_SOURCE_DOMAIN_MAP: dict[str, tuple[str, str, str, str | None]] = {
    "CONDITION_MONITORING_READING": (
        "condition_monitoring_reading", "condition_monitoring_reading_code", "asset_code", "deleted_at IS NULL",
    ),
    "PM_OCCURRENCE": (
        "pm_occurrence", "pm_occurrence_code", "asset_code", "deleted_at IS NULL",
    ),
    # installation_report has no soft-delete column (confirmed against
    # CANONICAL_SCHEMA.sql this MWO) and no asset_code column of its own
    # -- plant_equip_no is the nearest canonical-asset fact this domain
    # has, but CANONICAL_SCHEMA.sql's own header comment on that column
    # explicitly discloses it as "an informal reference with NO foreign
    # key" (weaker than condition_monitoring_reading.asset_code/
    # pm_occurrence.asset_code, which are what those domains actually key
    # their real operational work on) -- _resolve_canonical_asset_code()
    # below re-verifies the value against asset_registry before treating
    # it as canonical, so an unresolvable plant_equip_no degrades to "no
    # resolvable canonical asset" (Chief's own R4 Section 5 fallback)
    # rather than propagating a bad value into ltsa_finding.asset_code's
    # own real FK. (pump_tag_number, by contrast, is a column on
    # document_field_extraction, a different table entirely -- not
    # installation_report; confirmed directly against CANONICAL_SCHEMA.sql
    # this MWO after an initial mismatch caught by this repository's own
    # test suite.)
    "INSTALLATION_REPORT": (
        "installation_report", "installation_code", "plant_equip_no", None,
    ),
}

_UPDATABLE_FIELDS = (
    "finding_text", "status", "severity", "recommendation", "action",
    "owner_pic", "opened_date", "closed_date",
)

_SELECT_COLUMNS = (
    "finding_code, source_domain, source_record_code, asset_code, finding_text, status, severity, "
    "recommendation, action, owner_pic, opened_date, closed_date, source_reference, "
    "created_at, created_by, updated_at, updated_by"
)


def _new_code() -> str:
    return f"LTSAFND-{uuid.uuid4().hex[:12].upper()}"


class LtsaFindingRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def _resolve_canonical_asset_code(self, source_domain: str, source_record_code: str) -> str | None:
        if source_domain not in _SOURCE_DOMAIN_MAP:
            raise InvalidSourceDomain(source_domain)
        table, pk_col, asset_col, extra_where = _SOURCE_DOMAIN_MAP[source_domain]
        where = f"{pk_col} = {_sql(source_record_code)}"
        if extra_where:
            where += f" AND {extra_where}"
        rows = _json_query(f"SELECT {asset_col} AS canonical_asset_code FROM {table} WHERE {where}", self._runner)
        if not rows:
            raise SourceRecordNotFound(f"{source_domain}:{source_record_code}")
        candidate = rows[0]["canonical_asset_code"]
        if candidate is None:
            return None
        # Defensive re-verification against asset_registry (the proven
        # canonical asset identity authority) -- none of the 3 domains'
        # own asset-identifying columns carry a real DB FK there, so a
        # stale/malformed value must degrade to "no resolvable canonical
        # asset", never be propagated into ltsa_finding.asset_code's own
        # real FK as if it were trustworthy.
        exists = _json_query(f"SELECT 1 AS ok FROM asset_registry WHERE asset_code = {_sql(candidate)}", self._runner)
        return candidate if exists else None

    def find_by_code(self, finding_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM ltsa_finding WHERE finding_code = {_sql(finding_code)}", self._runner
        )
        return rows[0] if rows else None

    def find_by_code_with_area(self, finding_code: str) -> dict | None:
        # Same columns as find_by_code, plus the finding's resolved
        # asset_registry.area (never a new column on ltsa_finding itself
        # -- MA/area is always resolved at query time, per this MWO's own
        # R2 read-model design) so callers can apply
        # pump_area_scope.is_area_in_scope() without a second query.
        select_cols = ", ".join(f"f.{col.strip()}" for col in _SELECT_COLUMNS.split(","))
        rows = _json_query(
            f"SELECT {select_cols}, a.area AS asset_area FROM ltsa_finding f "
            "LEFT JOIN asset_registry a ON a.asset_code = f.asset_code "
            f"WHERE f.finding_code = {_sql(finding_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_findings(
        self,
        *,
        source_domain: str | None = None,
        source_record_code: str | None = None,
        asset_code: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        opened_after: str | None = None,
        opened_before: str | None = None,
        scope: frozenset[str] | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        clauses = ["1 = 1"]
        if source_domain is not None:
            clauses.append(f"f.source_domain = {_sql(source_domain)}")
        if source_record_code is not None:
            clauses.append(f"f.source_record_code = {_sql(source_record_code)}")
        if asset_code is not None:
            clauses.append(f"f.asset_code = {_sql(asset_code)}")
        if status is not None:
            clauses.append(f"f.status = {_sql(status)}")
        if severity is not None:
            clauses.append(f"f.severity = {_sql(severity)}")
        if opened_after is not None:
            clauses.append(f"f.opened_date >= {_sql(opened_after)}")
        if opened_before is not None:
            clauses.append(f"f.opened_date <= {_sql(opened_before)}")
        if scope is not None:
            if scope:
                values = ", ".join(_sql(area) for area in sorted(scope))
                clauses.append(f"a.area IN ({values})")
            else:
                clauses.append("FALSE")
        where_sql = " AND ".join(clauses)
        select_cols = ", ".join(f"f.{col.strip()}" for col in _SELECT_COLUMNS.split(","))
        rows = _json_query(
            f"SELECT {select_cols} FROM ltsa_finding f "
            "LEFT JOIN asset_registry a ON a.asset_code = f.asset_code "
            f"WHERE {where_sql} "
            "ORDER BY f.created_at DESC "
            f"LIMIT {int(limit)} OFFSET {int(offset)}",
            self._runner,
        )
        total_rows = _json_query(
            "SELECT COUNT(*) AS total FROM ltsa_finding f "
            "LEFT JOIN asset_registry a ON a.asset_code = f.asset_code "
            f"WHERE {where_sql}",
            self._runner,
        )
        total = int(total_rows[0]["total"]) if total_rows else 0
        return {"success": True, "data": rows, "items": rows, "count": len(rows), "total": total, "limit": limit, "offset": offset}

    def create(
        self,
        *,
        source_domain: str,
        source_record_code: str,
        asset_code: str | None = None,
        finding_text: str,
        status: str | None = None,
        severity: str | None = None,
        recommendation: str | None = None,
        action: str | None = None,
        owner_pic: str | None = None,
        opened_date: str | None = None,
        closed_date: str | None = None,
        source_reference: str | None = None,
        created_by: str,
    ) -> dict:
        canonical_asset_code = self._resolve_canonical_asset_code(source_domain, source_record_code)
        effective_asset_code = asset_code
        if canonical_asset_code is not None:
            if asset_code is not None and asset_code != canonical_asset_code:
                raise AssetMismatch(
                    f"supplied asset_code {asset_code!r} does not match "
                    f"{source_domain}:{source_record_code}'s own asset {canonical_asset_code!r}"
                )
            # Prefer deriving from the canonical source transaction when
            # unambiguous (Chief's own R4 Section 5 instruction), even
            # when the caller already supplied the same value.
            effective_asset_code = canonical_asset_code
        if status == "CLOSED" and closed_date is None:
            raise ClosedRequiresClosedDate("status=CLOSED requires closed_date")

        code = _new_code()
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO ltsa_finding "
                "(finding_code, source_domain, source_record_code, asset_code, finding_text, status, severity, "
                "recommendation, action, owner_pic, opened_date, closed_date, source_reference, created_by, updated_by) "
                f"VALUES ({_sql(code)}, {_sql(source_domain)}, {_sql(source_record_code)}, {_sql(effective_asset_code)}, "
                f"{_sql(finding_text)}, {_sql(status)}, {_sql(severity)}, {_sql(recommendation)}, {_sql(action)}, "
                f"{_sql(owner_pic)}, {_sql(opened_date)}, {_sql(closed_date)}, {_sql(source_reference)}, "
                f"{_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'LTSA_FINDING', finding_code, '__record__', NULL, row_to_json(ins)::text, "
                f"{_sql(created_by)}, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def update(self, finding_code: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self.find_by_code(finding_code)
        if existing is None:
            return None
        changes = {k: v for k, v in values.items() if k in _UPDATABLE_FIELDS}
        if not changes:
            return existing

        effective_status = changes.get("status", existing["status"])
        effective_closed_date = changes.get("closed_date", existing["closed_date"])
        if effective_status == "CLOSED" and effective_closed_date is None:
            raise ClosedRequiresClosedDate("status=CLOSED requires closed_date")

        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM ltsa_finding r "
                f"WHERE finding_code = {_sql(finding_code)}), upd AS ("
                f"UPDATE ltsa_finding SET {set_sql}, updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE finding_code = {_sql(finding_code)} "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'LTSA_FINDING', finding_code, '__record__', old.snapshot, row_to_json(upd)::text, "
                f"{_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None


__all__ = [
    "LtsaFindingRepository",
    "InvalidSourceDomain",
    "SourceRecordNotFound",
    "AssetMismatch",
    "ClosedRequiresClosedDate",
]
