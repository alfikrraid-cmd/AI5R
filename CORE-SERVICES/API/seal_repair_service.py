"""MWO-LTSA-SEAL-INSPECTION-REPAIR-001 -- engineering repair records for
physical mechanical seals. seal_repair is an ENGINEERING record, never
lifecycle-state truth: creating a repair here never writes a
seal_lifecycle_event row and never mutates seal_unit.status (even when
repair_result='SCRAPPED' -- SCRAP remains an explicit
seal_lifecycle_service.apply_lifecycle_event call, this MWO's own
explicit rule: "must NOT silently change unit to SCRAPPED").

STATUS RULE: repair creation requires seal_unit.status = 'UNDER_REPAIR'
(this MWO's own explicit rule, no exception).

CONTRADICTION GUARD: when inspection_id is supplied, the linked
inspection's own seal_unit_id must equal this repair's seal_unit_id --
rejected atomically in the same guarded statement, never checked/inserted
as two separate round-trips a partial failure could split apart.
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

from .seal_unit_repository import is_valid_uuid  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

REPAIR_RESULTS = frozenset({"COMPLETED", "PARTIAL", "FAILED", "SCRAPPED"})

_REPAIR_COLUMNS = (
    "repair_id, seal_unit_id, inspection_id, repair_date, repair_type, repair_action, "
    "parts_replaced, repair_result, performed_by, notes, source_reference, created_by, created_at"
)


class SealRepairError(ValueError):
    pass


class SealUnitNotFoundError(SealRepairError):
    pass


class InvalidRepairStateError(SealRepairError):
    pass


class InspectionMismatchError(SealRepairError):
    pass


class InvalidVocabularyError(SealRepairError):
    pass


def create_repair(
    runner: "DatabaseRunner",
    *,
    seal_unit_id: str,
    repair_date: str,
    repair_type: str,
    repair_action: str,
    created_by: str,
    inspection_id: str | None = None,
    parts_replaced: list | dict | None = None,
    repair_result: str | None = None,
    performed_by: str | None = None,
    notes: str | None = None,
    source_reference: str | None = None,
) -> dict:
    if repair_result is not None and repair_result not in REPAIR_RESULTS:
        raise InvalidVocabularyError(f"Unknown repair_result: {repair_result!r}")
    if not is_valid_uuid(seal_unit_id):
        raise SealUnitNotFoundError(seal_unit_id)
    if inspection_id is not None and not is_valid_uuid(inspection_id):
        raise InspectionMismatchError(inspection_id)

    inspection_guard_sql = "TRUE"
    if inspection_id is not None:
        inspection_guard_sql = (
            f"EXISTS (SELECT 1 FROM seal_inspection "
            f"WHERE inspection_id = {_sql(inspection_id)} AND seal_unit_id = status_ok.seal_unit_id)"
        )

    parts_sql = "NULL" if parts_replaced is None else f"{_sql(json.dumps(parts_replaced))}::jsonb"

    script = f"""
WITH locked AS (
    SELECT seal_unit_id, status FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}
),
status_ok AS (
    SELECT * FROM locked WHERE status = 'UNDER_REPAIR'
),
inspection_ok AS (
    SELECT * FROM status_ok WHERE {inspection_guard_sql}
),
repair_ins AS (
    INSERT INTO seal_repair
        (seal_unit_id, inspection_id, repair_date, repair_type, repair_action, parts_replaced,
         repair_result, performed_by, notes, source_reference, created_by)
    SELECT seal_unit_id, {_sql(inspection_id)}, {_sql(repair_date)}::timestamptz, {_sql(repair_type)},
           {_sql(repair_action)}, {parts_sql}, {_sql(repair_result)}, {_sql(performed_by)}, {_sql(notes)},
           {_sql(source_reference)}, {_sql(created_by)}
    FROM inspection_ok
    RETURNING {_REPAIR_COLUMNS}
)
SELECT row_to_json(t)::text FROM (
    SELECT
        (SELECT COUNT(*) FROM locked) AS unit_found,
        (SELECT COUNT(*) FROM status_ok) AS status_matched,
        (SELECT COUNT(*) FROM inspection_ok) AS inspection_matched,
        COALESCE((SELECT json_agg(row_to_json(r))::text FROM repair_ins r), '[]') AS repair_json
) t;
"""
    raw = runner.query_scalar(script.strip())
    if not raw:
        raise SealRepairError("Unexpected empty result creating repair")
    outcome = json.loads(raw)
    if int(outcome["unit_found"]) == 0:
        raise SealUnitNotFoundError(seal_unit_id)
    if int(outcome["status_matched"]) == 0:
        raise InvalidRepairStateError(
            f"seal_unit {seal_unit_id} is not UNDER_REPAIR; repair creation is rejected"
        )
    if int(outcome["inspection_matched"]) == 0:
        raise InspectionMismatchError(
            f"inspection {inspection_id!r} does not exist or belongs to a different seal_unit"
        )
    repairs = json.loads(outcome["repair_json"])
    if not repairs:
        raise SealRepairError("Unexpected: guard matched but no repair was inserted")
    return repairs[0]


class SealRepairRepository:
    """Read-only: find/list. No update()/delete() method exists anywhere
    on this class -- append-only by omission, the same discipline
    seal_lifecycle_event/seal_inspection already established."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_id(self, repair_id: str) -> dict | None:
        if not is_valid_uuid(repair_id):
            return None
        rows = _json_query(
            f"SELECT {_REPAIR_COLUMNS} FROM seal_repair WHERE repair_id = {_sql(repair_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_seal_unit(self, seal_unit_id: str) -> list[dict]:
        if not is_valid_uuid(seal_unit_id):
            return []
        return _json_query(
            f"SELECT {_REPAIR_COLUMNS} FROM seal_repair "
            f"WHERE seal_unit_id = {_sql(seal_unit_id)} "
            "ORDER BY repair_date ASC, repair_id ASC",
            self._runner,
        )

    def list_by_inspection_ids(self, inspection_ids: list[str]) -> list[dict]:
        """MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- seal_repair
        has no pump column (#6.3's own field list); a repair's only
        defensible historical pump is its linked inspection's pump
        (repair -> inspection -> inspection.pump_tag_number). One batched
        query for every inspection_id already fetched by the caller
        (e.g. "inspections for this pump"), never one query per
        inspection -- avoids the N+1 this MWO's own PERFORMANCE section
        forbids."""
        valid_ids = [i for i in inspection_ids if is_valid_uuid(i)]
        if not valid_ids:
            return []
        in_list = ", ".join(_sql(i) for i in valid_ids)
        return _json_query(
            f"SELECT {_REPAIR_COLUMNS} FROM seal_repair "
            f"WHERE inspection_id IN ({in_list}) "
            "ORDER BY repair_date ASC, repair_id ASC",
            self._runner,
        )


__all__ = [
    "REPAIR_RESULTS",
    "SealRepairError",
    "SealUnitNotFoundError",
    "InvalidRepairStateError",
    "InspectionMismatchError",
    "InvalidVocabularyError",
    "create_repair",
    "SealRepairRepository",
]
