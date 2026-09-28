"""MWO-LTSA-REPORTING-R4 -- real Postgres persistence for
condition_monitoring_reading_measurement (migration 037, Reporting R3
schema, the HYBRID generic child table). Same direct-Postgres,
CTE-shaped style as ConditionMonitoringReadingRepository -- no parallel
repository framework.

Exact schema column names from migration 037 only (measurement_id,
reading_id, measurement_code, measurement_label, value_numeric,
value_text, unit, measurement_side, source_label, source_reference,
verification_status, created_at/created_by/updated_at/updated_by) --
none invented.
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


class ReadingNotFound(Exception):
    """reading_id does not reference an existing, non-deleted
    condition_monitoring_reading row. Pre-checked here (rather than left
    to the DB FK violation) so the router can return a clean 404 --
    mirrors ConditionMonitoringReadingRepository.create_ad_hoc_draft's
    own None-on-missing-parent convention, just as an explicit
    exception since this repository's create() has other exception
    cases too and a bare None would be ambiguous between them."""


class EmptyMeasurementValue(Exception):
    """Neither value_numeric nor value_text was supplied. Pre-validated
    here (in addition to the DB's own CHECK constraint) so the router can
    return a clean 400 instead of a raw constraint-violation 500."""


_UPDATABLE_FIELDS = (
    "measurement_code", "measurement_label", "value_numeric", "value_text", "unit",
    "measurement_side", "source_label", "source_reference", "verification_status",
)

_SELECT_COLUMNS = (
    "measurement_id::text AS measurement_id, reading_id, measurement_code, measurement_label, "
    "value_numeric, value_text, unit, measurement_side, source_label, source_reference, "
    "verification_status, created_at, created_by, updated_at, updated_by"
)


class ConditionMonitoringMeasurementRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def _reading_exists(self, reading_id: str) -> bool:
        rows = _json_query(
            "SELECT 1 AS ok FROM condition_monitoring_reading "
            f"WHERE condition_monitoring_reading_code = {_sql(reading_id)} AND deleted_at IS NULL",
            self._runner,
        )
        return bool(rows)

    def find_by_id(self, measurement_id: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM condition_monitoring_reading_measurement "
            f"WHERE measurement_id = {_sql(measurement_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_reading(self, reading_id: str, *, scope: frozenset[str] | None = None) -> list[dict] | None:
        if not self._reading_exists(reading_id):
            return None
        scope_clause = ""
        if scope is not None:
            if scope:
                values = ", ".join(_sql(area) for area in sorted(scope))
                scope_clause = f"AND a.area IN ({values})"
            else:
                scope_clause = "AND FALSE"
        return _json_query(
            "SELECT m.measurement_id::text AS measurement_id, m.reading_id, m.measurement_code, m.measurement_label, "
            "m.value_numeric, m.value_text, m.unit, m.measurement_side, m.source_label, m.source_reference, "
            "m.verification_status, m.created_at, m.created_by, m.updated_at, m.updated_by "
            "FROM condition_monitoring_reading_measurement m "
            "JOIN condition_monitoring_reading r ON r.condition_monitoring_reading_code = m.reading_id "
            "LEFT JOIN asset_registry a ON a.asset_code = r.asset_code "
            f"WHERE m.reading_id = {_sql(reading_id)} {scope_clause} "
            "ORDER BY m.created_at",
            self._runner,
        )

    def create(
        self,
        *,
        reading_id: str,
        measurement_label: str,
        measurement_code: str | None = None,
        value_numeric: float | None = None,
        value_text: str | None = None,
        unit: str | None = None,
        measurement_side: str | None = None,
        source_label: str | None = None,
        source_reference: str | None = None,
        verification_status: str = "DRAFT",
        created_by: str,
    ) -> dict | None:
        if not self._reading_exists(reading_id):
            return None
        if value_numeric is None and value_text is None:
            raise EmptyMeasurementValue("at least one of value_numeric or value_text is required")

        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO condition_monitoring_reading_measurement "
                "(reading_id, measurement_code, measurement_label, value_numeric, value_text, unit, "
                "measurement_side, source_label, source_reference, verification_status, created_by, updated_by) "
                f"VALUES ({_sql(reading_id)}, {_sql(measurement_code)}, {_sql(measurement_label)}, "
                f"{_sql(value_numeric)}, {_sql(value_text)}, {_sql(unit)}, {_sql(measurement_side)}, "
                f"{_sql(source_label)}, {_sql(source_reference)}, {_sql(verification_status)}, "
                f"{_sql(created_by)}, {_sql(created_by)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'CONDITION_MONITORING_READING_MEASUREMENT', measurement_id, '__record__', NULL, "
                f"row_to_json(ins)::text, {_sql(created_by)}, 'CREATE' FROM ins) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def update(self, measurement_id: str, *, values: dict, updated_by: str) -> dict | None:
        existing = self.find_by_id(measurement_id)
        if existing is None:
            return None
        changes = {k: v for k, v in values.items() if k in _UPDATABLE_FIELDS}
        if not changes:
            return existing

        effective_numeric = changes.get("value_numeric", existing["value_numeric"])
        effective_text = changes.get("value_text", existing["value_text"])
        if effective_numeric is None and effective_text is None:
            raise EmptyMeasurementValue("at least one of value_numeric or value_text is required")

        set_sql = ", ".join(f"{col} = {_sql(val)}" for col, val in changes.items())
        rows = json.loads(
            self._runner.query_scalar(
                "WITH old AS (SELECT row_to_json(r)::text AS snapshot FROM condition_monitoring_reading_measurement r "
                f"WHERE measurement_id = {_sql(measurement_id)}), upd AS ("
                f"UPDATE condition_monitoring_reading_measurement SET {set_sql}, "
                f"updated_by = {_sql(updated_by)}, updated_at = NOW() "
                f"WHERE measurement_id = {_sql(measurement_id)} "
                f"RETURNING {_SELECT_COLUMNS}"
                "), audit AS (INSERT INTO record_change_history "
                "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason) "
                "SELECT 'CONDITION_MONITORING_READING_MEASUREMENT', measurement_id, '__record__', old.snapshot, "
                f"row_to_json(upd)::text, {_sql(updated_by)}, 'UPDATE' FROM upd CROSS JOIN old) "
                "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None


__all__ = ["ConditionMonitoringMeasurementRepository", "ReadingNotFound", "EmptyMeasurementValue"]
