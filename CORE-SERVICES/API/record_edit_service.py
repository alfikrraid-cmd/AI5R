"""MWO-LTSA-AUDIT-CHANGE-HISTORY-001 -- the ONE generic "Edit Value"
correction engine, reused by every domain via an explicit, allowlisted
EntityAdapter (never arbitrary SQL/field editing -- Hard Rule). Proven
end-to-end this MWO on two representative domains:
CONDITION_MONITORING_READING (reuses condition_monitoring_reading_
repository.py's own _MEASUREMENT_COLUMNS allowlist verbatim -- one
source of truth, never a second copy) and INSTALLATION_REPORT (a new,
explicit allowlist of correctable transcription fields -- identity/join
fields like plant_equip_no and seal_code are deliberately EXCLUDED,
since changing those would silently reassign which pump/seal a whole
report belongs to, not correct a value on it).

Edit sequence (Hard Rule, all 8 steps enforced here, in order):
  1. permission -- enforced by the router's require_permission("record.edit"),
     not here (this module has no HTTP/auth awareness).
  2. data scope -- resolve_area_scope() must already have been resolved by
     the caller; this module checks the target record's own asset value
     against it before allowing the read-old/write-new pair below.
  3. allowlisted field -- EntityAdapter.editable_fields membership.
  4. reason required -- non-empty string.
  5. read old canonical value -- one SELECT, same query also fetches the
     asset value scope needs (no separate round trip).
  6/7. write new value + append audit record -- ONE atomic SQL script
     (explicit BEGIN;...COMMIT;), executed as a single execute_script()
     call -- the same "one script, one atomic outcome" convention
     DatabaseRunner's own docstring already documents (a mid-script
     error aborts the whole transaction under Postgres's simple-query
     protocol, so a failed UPDATE never leaves an orphan audit row, and
     a failed audit INSERT never leaves an unaudited edit).
  8. actor derived server-side -- this module never accepts an actor
     identity as part of `new_value`/the request; `actor_id` is a
     required keyword the ROUTER supplies from the authenticated
     identity, the same _actor_id(current_user) pattern pm_occurrence.py/
     condition_monitoring.py's write routers already establish.

No-op (old == new, by value, not by string identity of the DB
representation) skips both the UPDATE and the audit INSERT entirely --
"do not create misleading history" (Hard Rule).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .condition_monitoring_reading_repository import _MEASUREMENT_COLUMNS  # noqa: E402
from .pump_area_scope import is_asset_in_scope  # noqa: E402


class RecordEditError(ValueError):
    """Base class for every rejected edit -- the router maps each
    subtype to its own HTTP status, never a bare 500."""


class UnknownEntityTypeError(RecordEditError):
    pass


class FieldNotEditableError(RecordEditError):
    pass


class RecordNotFoundError(RecordEditError):
    pass


class ReasonRequiredError(RecordEditError):
    pass


class OutOfScopeError(RecordEditError):
    pass


@dataclass(frozen=True, slots=True)
class EntityAdapter:
    entity_type: str
    table: str
    pk_column: str
    editable_fields: frozenset[str]
    # Column on the SAME table holding the pump tag, used to resolve
    # Area/MA scope via pump_area_scope.is_asset_in_scope(). None would
    # mean "not pump-attributable" -- not used by either adapter below,
    # since both CMON and Installation are pump-scoped domains.
    asset_field: str


CONDITION_MONITORING_READING_ADAPTER = EntityAdapter(
    entity_type="CONDITION_MONITORING_READING",
    table="condition_monitoring_reading",
    pk_column="condition_monitoring_reading_code",
    editable_fields=frozenset(_MEASUREMENT_COLUMNS),
    asset_field="asset_code",
)

# Installation Report -- plain transcription/observation fields only.
# Deliberately EXCLUDES: installation_code/report_no (identity),
# plant_equip_no/seal_code (join keys -- correcting these would silently
# reassign the report to a different pump/seal, not fix a value on it),
# every JSONB aggregate (bill_of_material/gland_observation/
# post_installation_readings/signatures/etc. -- structured sub-documents,
# out of this MWO's "explicit allowlisted editable FIELDS" scope; a
# future MWO can extend the adapter for JSONB sub-field correction),
# source_document_name (provenance, never correctable -- Hard Rule
# "NEVER overwrite original uploaded/source evidence" extends to the
# pointer identifying which evidence this report came from).
_INSTALLATION_REPORT_EDITABLE_FIELDS = frozenset(
    {
        "tso_no", "report_date", "customer", "address", "plant", "unit", "po_no",
        "packing_list_no", "location",
        "equipment_mfr", "model_type", "size", "configuration", "serial_no",
        "pump_type", "shaft_speed", "rotation",
        "seal_manufacture", "seal_type", "seal_arrangement", "seal_size",
        "material_code", "drawing_no", "seal_location",
        "liquid", "temperature_range", "specific_gravity", "viscosity",
        "flash_point", "boiling_point", "freeze_point", "vapor_press",
        "discharge_press", "suction_press", "differential_press",
        "stuffing_box_press", "seal_press", "corrosion_erosion_by",
        "api_plan", "flush_liquid", "flush_pressure", "flush_temp",
        "flush_flowrate", "buffer_barrier_press", "buffer_barrier_fluid",
        "quench_fluid",
        "basic_seal_condition", "gland_condition", "sleeve_condition",
        "shaft_condition", "bearing_condition", "gasket_condition",
        "radial_bearing_no", "thrust_bearing_no",
    }
)

INSTALLATION_REPORT_ADAPTER = EntityAdapter(
    entity_type="INSTALLATION_REPORT",
    table="installation_report",
    pk_column="installation_code",
    editable_fields=_INSTALLATION_REPORT_EDITABLE_FIELDS,
    asset_field="plant_equip_no",
)

ADAPTERS: dict[str, EntityAdapter] = {
    a.entity_type: a for a in (CONDITION_MONITORING_READING_ADAPTER, INSTALLATION_REPORT_ADAPTER)
}


def _to_audit_text(value: Any) -> str | None:
    """None stays SQL NULL (distinct from the text '0') -- everything
    else becomes its plain string form, matching migration 017's own
    "plain string representation" convention."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _values_equal(old: Any, new: Any) -> bool:
    if old is None or new is None:
        return old is None and new is None
    return _to_audit_text(old) == _to_audit_text(new)


def edit_value(
    *,
    entity_type: str,
    entity_id: str,
    field_name: str,
    new_value: Any,
    reason: str,
    actor_id: str,
    scope: frozenset[str] | None,
    runner: Any,
    pump_gateway: Any,
    source_reference: str | None = None,
) -> dict:
    adapter = ADAPTERS.get(entity_type)
    if adapter is None:
        raise UnknownEntityTypeError(f"unknown entity_type {entity_type!r}")
    if field_name not in adapter.editable_fields:
        raise FieldNotEditableError(f"{field_name!r} is not an editable field of {entity_type}")
    if not reason or not reason.strip():
        raise ReasonRequiredError("reason is required")

    select_cols = f"{adapter.pk_column}, {field_name}, {adapter.asset_field}"
    rows = _json_query(
        f"SELECT {select_cols} FROM {adapter.table} WHERE {adapter.pk_column} = {_sql(entity_id)}",
        runner,
    )
    if not rows:
        raise RecordNotFoundError(f"no {entity_type} with id {entity_id!r}")
    current = rows[0]

    if scope is not None:
        asset_value = current.get(adapter.asset_field)
        if not is_asset_in_scope(asset_value, scope, pump_gateway):
            # Same safe not-found semantics as every other cross-scope
            # denial this session's own closures already established --
            # never a distinct 403 that would confirm the record exists
            # but is out of scope.
            raise RecordNotFoundError(f"no {entity_type} with id {entity_id!r}")

    old_value = current.get(field_name)
    if _values_equal(old_value, new_value):
        return {
            "no_op": True,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "value": old_value,
        }

    script = (
        "BEGIN;\n"
        f"UPDATE {adapter.table} SET {field_name} = {_sql(new_value)} "
        f"WHERE {adapter.pk_column} = {_sql(entity_id)};\n"
        "INSERT INTO record_change_history "
        "(entity_type, entity_id, field_name, old_value, new_value, changed_by, reason, source_reference) VALUES ("
        f"{_sql(entity_type)}, {_sql(entity_id)}, {_sql(field_name)}, {_sql(_to_audit_text(old_value))}, "
        f"{_sql(_to_audit_text(new_value))}, {_sql(actor_id)}, {_sql(reason)}, {_sql(source_reference)});\n"
        "COMMIT;\n"
    )
    runner.execute_script(script)

    return {
        "no_op": False,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_name": field_name,
        "old_value": old_value,
        "new_value": new_value,
    }


def get_history(entity_type: str, entity_id: str, *, history_repository) -> list[dict]:
    if entity_type not in ADAPTERS:
        raise UnknownEntityTypeError(f"unknown entity_type {entity_type!r}")
    return history_repository.list_for_entity(entity_type, entity_id)


__all__ = [
    "EntityAdapter",
    "CONDITION_MONITORING_READING_ADAPTER",
    "INSTALLATION_REPORT_ADAPTER",
    "ADAPTERS",
    "RecordEditError",
    "UnknownEntityTypeError",
    "FieldNotEditableError",
    "RecordNotFoundError",
    "ReasonRequiredError",
    "OutOfScopeError",
    "edit_value",
    "get_history",
]
