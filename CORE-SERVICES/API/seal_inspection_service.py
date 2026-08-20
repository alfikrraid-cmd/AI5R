"""MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- engineering inspection records
for physical mechanical seals. seal_inspection/seal_inspection_finding
are ENGINEERING evidence, never lifecycle-state truth: creating an
inspection here never writes a seal_lifecycle_event row and never
mutates seal_unit.status/current_pump_tag_number -- that stays the
exclusive job of seal_lifecycle_service.apply_lifecycle_event, called
explicitly (SEND_FOR_INSPECTION/INSPECTION_COMPLETED/...), never
inferred from an inspection outcome.

STATUS RULE (audited, disclosed, not silently decided): inspection
creation requires seal_unit NOT INSTALLED for every inspection_type,
including GENERAL. This MWO conditionally allows an in-situ exception
only "if repository/domain evidence supports in-situ inspection" -- a
repo-wide audit found none: condition_monitoring_reading is pump-level
OPERATIONAL telemetry (temperatures/pressures/vibration), a different
domain from a physical mechanical-seal TEARDOWN/component inspection,
and no other repository models an installed-seal component inspection.
No exception is granted here; a future MWO may add one only if genuine
in-situ inspection evidence is found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .seal_unit_repository import is_valid_uuid  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

INSPECTION_TYPES = frozenset({"RECEIVING", "POST_REMOVAL", "PRE_REPAIR", "POST_REPAIR", "GENERAL"})
DISPOSITIONS = frozenset({"RETURN_TO_STOCK", "REPAIR_REQUIRED", "SCRAP_RECOMMENDED", "MONITOR"})
FINDING_COMPONENTS = frozenset(
    {"SEAL_FACE", "MATING_RING", "O_RING", "SLEEVE", "SPRING", "DRIVE_PIN", "SET_SCREW", "GLAND", "OTHER"}
)

_INSPECTION_COLUMNS = (
    "inspection_id, seal_unit_id, inspection_date, pump_tag_number, inspection_type, "
    "overall_condition, failure_mode, root_cause, recommendation, disposition, inspected_by, "
    "notes, source_reference, created_by, created_at"
)
_FINDING_COLUMNS = (
    "finding_id, inspection_id, component, condition, measurement_name, measured_value, unit, "
    "acceptance_min, acceptance_max, finding, action_required, created_at"
)


class SealInspectionError(ValueError):
    pass


class SealUnitNotFoundError(SealInspectionError):
    pass


class InvalidInspectionStateError(SealInspectionError):
    pass


class UnknownPumpError(SealInspectionError):
    pass


class InvalidVocabularyError(SealInspectionError):
    pass


class SealInspectionFinding:
    __slots__ = (
        "component", "condition", "measurement_name", "measured_value", "unit",
        "acceptance_min", "acceptance_max", "finding", "action_required",
    )

    def __init__(
        self, *, component: str, condition: str | None = None, measurement_name: str | None = None,
        measured_value: float | None = None, unit: str | None = None, acceptance_min: float | None = None,
        acceptance_max: float | None = None, finding: str | None = None, action_required: str | None = None,
    ) -> None:
        self.component = component
        self.condition = condition
        self.measurement_name = measurement_name
        self.measured_value = measured_value
        self.unit = unit
        self.acceptance_min = acceptance_min
        self.acceptance_max = acceptance_max
        self.finding = finding
        self.action_required = action_required


def create_inspection(
    runner: "DatabaseRunner",
    *,
    seal_unit_id: str,
    inspection_date: str,
    inspection_type: str,
    created_by: str,
    pump_tag_number: str | None = None,
    overall_condition: str | None = None,
    failure_mode: str | None = None,
    root_cause: str | None = None,
    recommendation: str | None = None,
    disposition: str | None = None,
    inspected_by: str | None = None,
    notes: str | None = None,
    source_reference: str | None = None,
    findings: list[SealInspectionFinding] | None = None,
) -> dict:
    """ATOMICITY: the inspection header row and every finding row are
    written by ONE compound SQL statement (the same guarded-CTE pattern
    seal_lifecycle_service.apply_lifecycle_event already established) --
    a status-guard or FK failure aborts before anything is inserted, so a
    partially-written inspection (header with no findings, or the reverse)
    can never persist."""
    if inspection_type not in INSPECTION_TYPES:
        raise InvalidVocabularyError(f"Unknown inspection_type: {inspection_type!r}")
    if disposition is not None and disposition not in DISPOSITIONS:
        raise InvalidVocabularyError(f"Unknown disposition: {disposition!r}")
    if not is_valid_uuid(seal_unit_id):
        raise SealUnitNotFoundError(seal_unit_id)

    findings = findings or []
    for f in findings:
        if f.component not in FINDING_COMPONENTS:
            raise InvalidVocabularyError(f"Unknown finding component: {f.component!r}")

    pump_guard_sql = "TRUE"
    if pump_tag_number:
        pump_guard_sql = f"EXISTS (SELECT 1 FROM ltsa_pumps WHERE tag_number = {_sql(pump_tag_number)})"

    script = f"""
WITH locked AS (
    SELECT seal_unit_id, status FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}
),
status_ok AS (
    SELECT * FROM locked WHERE status <> 'INSTALLED'
),
pump_ok AS (
    SELECT * FROM status_ok WHERE {pump_guard_sql}
),
inspection_ins AS (
    INSERT INTO seal_inspection
        (seal_unit_id, inspection_date, pump_tag_number, inspection_type, overall_condition,
         failure_mode, root_cause, recommendation, disposition, inspected_by, notes,
         source_reference, created_by)
    SELECT seal_unit_id, {_sql(inspection_date)}::timestamptz, {_sql(pump_tag_number)},
           {_sql(inspection_type)}, {_sql(overall_condition)}, {_sql(failure_mode)}, {_sql(root_cause)},
           {_sql(recommendation)}, {_sql(disposition)}, {_sql(inspected_by)}, {_sql(notes)},
           {_sql(source_reference)}, {_sql(created_by)}
    FROM pump_ok
    RETURNING {_INSPECTION_COLUMNS}
)"""

    if findings:
        # Every literal is explicitly cast: a VALUES() column that is NULL
        # in every row (e.g. no finding in this batch sets acceptance_min)
        # has no non-null literal to infer a type from, and Postgres
        # defaults an all-NULL derived-table column to `text` -- which
        # then fails against the NUMERIC target column downstream. Casting
        # every cell here removes the guesswork entirely.
        values_rows = ", ".join(
            "(" + ", ".join(
                [
                    f"{_sql(f.component)}::text", f"{_sql(f.condition)}::text",
                    f"{_sql(f.measurement_name)}::text",
                    ("NULL" if f.measured_value is None else str(f.measured_value)) + "::numeric",
                    f"{_sql(f.unit)}::text",
                    ("NULL" if f.acceptance_min is None else str(f.acceptance_min)) + "::numeric",
                    ("NULL" if f.acceptance_max is None else str(f.acceptance_max)) + "::numeric",
                    f"{_sql(f.finding)}::text", f"{_sql(f.action_required)}::text",
                ]
            ) + ")"
            for f in findings
        )
        script += f""",
finding_ins AS (
    INSERT INTO seal_inspection_finding
        (inspection_id, component, condition, measurement_name, measured_value, unit,
         acceptance_min, acceptance_max, finding, action_required)
    SELECT inspection_ins.inspection_id, v.component, v.condition, v.measurement_name,
           v.measured_value, v.unit, v.acceptance_min, v.acceptance_max, v.finding, v.action_required
    FROM inspection_ins, (VALUES {values_rows}) AS v(
        component, condition, measurement_name, measured_value, unit,
        acceptance_min, acceptance_max, finding, action_required
    )
    RETURNING {_FINDING_COLUMNS}
)"""
        findings_select = "COALESCE((SELECT json_agg(row_to_json(f))::text FROM finding_ins f), '[]')"
    else:
        findings_select = "'[]'"

    script += f"""
SELECT row_to_json(t)::text FROM (
    SELECT
        (SELECT COUNT(*) FROM locked) AS unit_found,
        (SELECT COUNT(*) FROM status_ok) AS status_matched,
        (SELECT COUNT(*) FROM pump_ok) AS pump_matched,
        COALESCE((SELECT json_agg(row_to_json(i))::text FROM inspection_ins i), '[]') AS inspection_json,
        {findings_select} AS findings_json
) t;
"""
    raw = runner.query_scalar(script.strip())
    if not raw:
        raise SealInspectionError("Unexpected empty result creating inspection")
    outcome = json.loads(raw)
    if int(outcome["unit_found"]) == 0:
        raise SealUnitNotFoundError(seal_unit_id)
    if int(outcome["status_matched"]) == 0:
        raise InvalidInspectionStateError(
            f"seal_unit {seal_unit_id} is INSTALLED; inspection requires the unit to be removed first"
        )
    if int(outcome["pump_matched"]) == 0:
        raise UnknownPumpError(pump_tag_number)
    inspections = json.loads(outcome["inspection_json"])
    if not inspections:
        raise SealInspectionError("Unexpected: guard matched but no inspection was inserted")
    inspection = inspections[0]
    inspection["findings"] = json.loads(outcome["findings_json"])
    return inspection


class SealInspectionRepository:
    """Read-only: find/list. No update()/delete() method exists anywhere
    on this class -- append-only by omission, the same discipline
    seal_lifecycle_event already established."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_id(self, inspection_id: str) -> dict | None:
        if not is_valid_uuid(inspection_id):
            return None
        rows = _json_query(
            f"SELECT {_INSPECTION_COLUMNS} FROM seal_inspection WHERE inspection_id = {_sql(inspection_id)}",
            self._runner,
        )
        if not rows:
            return None
        inspection = rows[0]
        inspection["findings"] = _json_query(
            f"SELECT {_FINDING_COLUMNS} FROM seal_inspection_finding "
            f"WHERE inspection_id = {_sql(inspection_id)} ORDER BY created_at ASC, finding_id ASC",
            self._runner,
        )
        return inspection

    def list_by_seal_unit(self, seal_unit_id: str) -> list[dict]:
        if not is_valid_uuid(seal_unit_id):
            return []
        return _json_query(
            f"SELECT {_INSPECTION_COLUMNS} FROM seal_inspection "
            f"WHERE seal_unit_id = {_sql(seal_unit_id)} "
            "ORDER BY inspection_date ASC, inspection_id ASC",
            self._runner,
        )

    def list_by_pump(self, pump_tag_number: str) -> list[dict]:
        return _json_query(
            f"SELECT {_INSPECTION_COLUMNS} FROM seal_inspection "
            f"WHERE pump_tag_number = {_sql(pump_tag_number)} "
            "ORDER BY inspection_date ASC, inspection_id ASC",
            self._runner,
        )


__all__ = [
    "INSPECTION_TYPES",
    "DISPOSITIONS",
    "FINDING_COMPONENTS",
    "SealInspectionError",
    "SealUnitNotFoundError",
    "InvalidInspectionStateError",
    "UnknownPumpError",
    "InvalidVocabularyError",
    "SealInspectionFinding",
    "create_inspection",
    "SealInspectionRepository",
]
