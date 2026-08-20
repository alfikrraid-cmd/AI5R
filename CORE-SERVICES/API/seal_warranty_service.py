"""MWO-LTSA-SEAL-WARRANTY-ASSESSMENT-001 -- mechanical-seal warranty
window calculation and technical warranty assessment.

CRITICAL DISTINCTION (this MWO's own frozen rule): a warranty WINDOW is a
pure time calculation (installation_date -> +18 calendar months);
warranty DECISION (ACCEPTED/REJECTED) is a separate, explicit, human,
auditable act. This module's window calculation never sets ACCEPTED or
REJECTED -- only PENDING_EXAMINATION at creation; decide_assessment() is
the ONE place a human-authorized decision is recorded, and only once
(guarded transition out of PENDING_EXAMINATION, never re-decidable --
this MWO's own IMMUTABILITY rule, the smallest model that preserves
decision history without a second audit engine: not a pure INSERT-only
table like seal_lifecycle_event/seal_inspection/seal_repair, because a
warranty case genuinely has one mutable field -- its own decision,
transitioned exactly once and then permanently frozen).

AUTHORITATIVE INSTALLATION DATE: always installation_event.event_at from
an existing seal_lifecycle_event row where event_type = 'INSTALL' and
seal_unit_id matches -- never PO/delivery/receipt/manufacture/stock-
entry/registration date, and never re-derived or guessed.
"""

from __future__ import annotations

import calendar
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .seal_unit_repository import is_valid_uuid  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

WARRANTY_MONTHS = 18

WINDOW_STATUSES = frozenset({"WITHIN_WARRANTY_WINDOW", "OUT_OF_WARRANTY", "INSUFFICIENT_DATA"})
DECISION_STATUSES = frozenset({"PENDING_EXAMINATION", "ACCEPTED", "REJECTED", "NOT_APPLICABLE"})
_DECISIONS_REQUIRING_INSPECTION = frozenset({"ACCEPTED", "REJECTED"})

_ASSESSMENT_COLUMNS = (
    "assessment_id, seal_unit_id, installation_event_id, inspection_id, claim_date, failure_date, "
    "installation_date, warranty_end, window_status, decision_status, technical_reason, decision_reason, "
    "source_reference, assessed_by, decided_by, created_by, assessed_at, decided_at, created_at"
)
# Same columns, table-qualified: seal_warranty_assessment and
# seal_lifecycle_event both have seal_unit_id/source_reference/
# created_by/created_at -- ambiguous unqualified in the JOIN queries
# below, so those use this list instead of _ASSESSMENT_COLUMNS.
_ASSESSMENT_COLUMNS_QUALIFIED = ", ".join(f"a.{col.strip()}" for col in _ASSESSMENT_COLUMNS.split(","))


class SealWarrantyError(ValueError):
    pass


class SealUnitNotFoundError(SealWarrantyError):
    pass


class InstallationEventNotFoundError(SealWarrantyError):
    pass


class NotAnInstallEventError(SealWarrantyError):
    pass


class InstallationEventMismatchError(SealWarrantyError):
    pass


class InspectionMismatchError(SealWarrantyError):
    pass


class InvalidChronologyError(SealWarrantyError):
    pass


class AssessmentNotFoundError(SealWarrantyError):
    pass


class AlreadyDecidedError(SealWarrantyError):
    pass


class MissingInspectionForDecisionError(SealWarrantyError):
    pass


class MissingDecisionReasonError(SealWarrantyError):
    pass


class InvalidDecisionError(SealWarrantyError):
    pass


def _add_calendar_months(dt: datetime, months: int) -> datetime:
    """Real calendar-month arithmetic (never fixed 548/547 days, this
    MWO's own explicit rule): a shorter target month clamps the day (e.g.
    2026-08-31 + 6 months -> 2027-02-28, not an overflow into March)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class WarrantyWindow:
    installation_date: datetime
    warranty_end: datetime
    window_status: str


def calculate_warranty_window(
    installation_date: datetime, *, failure_date: datetime | None = None, claim_date: datetime | None = None
) -> WarrantyWindow:
    """Pure, read-only, no DB access -- the reusable window-calculation
    service this MWO's own WARRANTY WINDOW SERVICE section requires.
    Never persists anything merely because it was called.

    Reference-date priority: failure_date (the actual technical event)
    if given, else claim_date (a claim being filed is itself a real,
    semantically defensible reference point) if given, else
    INSUFFICIENT_DATA -- never guessed as "now"."""
    warranty_end = _add_calendar_months(installation_date, WARRANTY_MONTHS)
    reference = failure_date if failure_date is not None else claim_date

    if failure_date is not None and failure_date < installation_date:
        raise InvalidChronologyError("failure_date cannot be before installation_date")

    if reference is None:
        window_status = "INSUFFICIENT_DATA"
    elif reference <= warranty_end:
        # Boundary rule (this MWO's own explicit decision, documented and
        # tested): exactly on warranty_end is still WITHIN warranty.
        window_status = "WITHIN_WARRANTY_WINDOW"
    else:
        window_status = "OUT_OF_WARRANTY"

    return WarrantyWindow(installation_date=installation_date, warranty_end=warranty_end, window_status=window_status)


def create_warranty_assessment(
    runner: "DatabaseRunner",
    *,
    seal_unit_id: str,
    installation_event_id: str,
    created_by: str,
    claim_date: str | None = None,
    failure_date: str | None = None,
    inspection_id: str | None = None,
    source_reference: str | None = None,
) -> dict:
    if not is_valid_uuid(seal_unit_id):
        raise SealUnitNotFoundError(seal_unit_id)
    if not is_valid_uuid(installation_event_id):
        raise InstallationEventNotFoundError(installation_event_id)
    if inspection_id is not None and not is_valid_uuid(inspection_id):
        raise InspectionMismatchError(inspection_id)

    # These are lookups against immutable, already-append-only facts
    # (seal_lifecycle_event/seal_inspection rows never change after
    # creation -- #6.2/#6.3's own discipline), so resolving them with a
    # plain read before the guarded write below introduces no race a
    # concurrent mutation could exploit -- unlike seal_unit.status (#6.2),
    # nothing here is ever updated in place.
    unit_rows = _json_query(f"SELECT seal_unit_id FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}", runner)
    if not unit_rows:
        raise SealUnitNotFoundError(seal_unit_id)

    event_rows = _json_query(
        f"SELECT event_id, seal_unit_id, event_type, event_at FROM seal_lifecycle_event "
        f"WHERE event_id = {_sql(installation_event_id)}",
        runner,
    )
    if not event_rows:
        raise InstallationEventNotFoundError(installation_event_id)
    event = event_rows[0]
    if event["event_type"] != "INSTALL":
        raise NotAnInstallEventError(installation_event_id)
    if event["seal_unit_id"] != seal_unit_id:
        raise InstallationEventMismatchError(installation_event_id)

    if inspection_id is not None:
        inspection_rows = _json_query(
            f"SELECT inspection_id FROM seal_inspection "
            f"WHERE inspection_id = {_sql(inspection_id)} AND seal_unit_id = {_sql(seal_unit_id)}",
            runner,
        )
        if not inspection_rows:
            raise InspectionMismatchError(inspection_id)

    installation_date = _parse(event["event_at"])
    window = calculate_warranty_window(
        installation_date, failure_date=_parse(failure_date), claim_date=_parse(claim_date)
    )

    script = f"""
WITH unit_ok AS (
    SELECT seal_unit_id FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}
),
assessment_ins AS (
    INSERT INTO seal_warranty_assessment
        (seal_unit_id, installation_event_id, inspection_id, claim_date, failure_date, installation_date,
         warranty_end, window_status, decision_status, source_reference, created_by)
    SELECT {_sql(seal_unit_id)}, {_sql(installation_event_id)}, {_sql(inspection_id)}, {_sql(claim_date)}::timestamptz,
           {_sql(failure_date)}::timestamptz, {_sql(window.installation_date.isoformat())}::timestamptz,
           {_sql(window.warranty_end.isoformat())}::timestamptz, {_sql(window.window_status)}, 'PENDING_EXAMINATION',
           {_sql(source_reference)}, {_sql(created_by)}
    FROM unit_ok
    RETURNING {_ASSESSMENT_COLUMNS}
)
SELECT COALESCE((SELECT json_agg(row_to_json(a))::text FROM assessment_ins a), '[]');
"""
    raw = runner.query_scalar(script.strip())
    rows = json.loads(raw or "[]")
    if not rows:
        raise SealWarrantyError("Unexpected: seal_unit vanished between validation and insert")
    return rows[0]


def decide_assessment(
    runner: "DatabaseRunner",
    *,
    assessment_id: str,
    decision: str,
    decision_reason: str | None,
    decided_by: str,
    inspection_id: str | None = None,
) -> dict:
    """ONE guarded transition, PENDING_EXAMINATION -> a terminal decision
    status, never repeatable (this MWO's own IMMUTABILITY rule). If the
    assessment already has an inspection_id, that link is never replaced
    by this call's inspection_id -- only used to fill in a still-empty
    link, so a finalized evidence link can never be silently overwritten.
    """
    if decision not in DECISION_STATUSES or decision == "PENDING_EXAMINATION":
        raise InvalidDecisionError(f"Unknown or non-terminal decision: {decision!r}")
    if not (decision_reason or "").strip():
        raise MissingDecisionReasonError("decision_reason is required")
    if not is_valid_uuid(assessment_id):
        raise AssessmentNotFoundError(assessment_id)
    if inspection_id is not None and not is_valid_uuid(inspection_id):
        raise InspectionMismatchError(inspection_id)

    require_inspection_sql = "TRUE"
    if decision in _DECISIONS_REQUIRING_INSPECTION:
        # References pending_ok (this guard's own FROM clause), not
        # locked -- pending_ok inherits every column from locked via
        # SELECT *, so this resolves the same values without the
        # out-of-scope alias error.
        require_inspection_sql = (
            "COALESCE(pending_ok.inspection_id, " + _sql(inspection_id) + ") IS NOT NULL "
            "AND EXISTS (SELECT 1 FROM seal_inspection WHERE inspection_id = "
            "COALESCE(pending_ok.inspection_id, " + _sql(inspection_id) + ") "
            "AND seal_unit_id = pending_ok.seal_unit_id)"
        )

    script = f"""
WITH locked AS (
    SELECT assessment_id, seal_unit_id, decision_status, inspection_id FROM seal_warranty_assessment
    WHERE assessment_id = {_sql(assessment_id)} FOR UPDATE
),
pending_ok AS (
    SELECT * FROM locked WHERE decision_status = 'PENDING_EXAMINATION'
),
inspection_ok AS (
    SELECT * FROM pending_ok WHERE {require_inspection_sql}
),
decided_upd AS (
    UPDATE seal_warranty_assessment SET
        decision_status = {_sql(decision)},
        decision_reason = {_sql(decision_reason)},
        decided_by = {_sql(decided_by)},
        decided_at = NOW(),
        inspection_id = COALESCE(seal_warranty_assessment.inspection_id, {_sql(inspection_id)})
    WHERE assessment_id IN (SELECT assessment_id FROM inspection_ok)
    RETURNING {_ASSESSMENT_COLUMNS}
)
SELECT row_to_json(t)::text FROM (
    SELECT
        (SELECT COUNT(*) FROM locked) AS assessment_found,
        (SELECT COUNT(*) FROM pending_ok) AS pending_matched,
        (SELECT COUNT(*) FROM inspection_ok) AS inspection_matched,
        COALESCE((SELECT json_agg(row_to_json(d))::text FROM decided_upd d), '[]') AS decided_json
) t;
"""
    raw = runner.query_scalar(script.strip())
    if not raw:
        raise SealWarrantyError("Unexpected empty result deciding assessment")
    outcome = json.loads(raw)
    if int(outcome["assessment_found"]) == 0:
        raise AssessmentNotFoundError(assessment_id)
    if int(outcome["pending_matched"]) == 0:
        raise AlreadyDecidedError(f"assessment {assessment_id} already has a final decision")
    if int(outcome["inspection_matched"]) == 0:
        raise MissingInspectionForDecisionError(
            f"{decision} requires a linked inspection belonging to the same seal_unit"
        )
    decided = json.loads(outcome["decided_json"])
    if not decided:
        raise SealWarrantyError("Unexpected: guard matched but no row was updated")
    return decided[0]


class SealWarrantyAssessmentRepository:
    """Read-only from outside this module: find/list. The only mutation
    path anywhere is decide_assessment()'s own single guarded transition
    -- there is no generic update()/delete() method."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_id(self, assessment_id: str) -> dict | None:
        if not is_valid_uuid(assessment_id):
            return None
        rows = _json_query(
            f"SELECT {_ASSESSMENT_COLUMNS_QUALIFIED}, le.pump_tag_number AS installation_pump_tag_number "
            "FROM seal_warranty_assessment a "
            "JOIN seal_lifecycle_event le ON le.event_id = a.installation_event_id "
            f"WHERE a.assessment_id = {_sql(assessment_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_seal_unit(self, seal_unit_id: str) -> list[dict]:
        if not is_valid_uuid(seal_unit_id):
            return []
        return _json_query(
            f"SELECT {_ASSESSMENT_COLUMNS_QUALIFIED}, le.pump_tag_number AS installation_pump_tag_number "
            "FROM seal_warranty_assessment a "
            "JOIN seal_lifecycle_event le ON le.event_id = a.installation_event_id "
            f"WHERE a.seal_unit_id = {_sql(seal_unit_id)} "
            "ORDER BY a.installation_date ASC, a.assessment_id ASC",
            self._runner,
        )

    def list_by_pump(self, pump_tag_number: str) -> list[dict]:
        """MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 -- warranty's
        historical pump derives ONLY from its linked INSTALL event's own
        pump_tag_number (this module's own already-established JOIN,
        reused here with a different WHERE clause), never
        seal_unit.current_pump_tag_number."""
        return _json_query(
            f"SELECT {_ASSESSMENT_COLUMNS_QUALIFIED}, le.pump_tag_number AS installation_pump_tag_number "
            "FROM seal_warranty_assessment a "
            "JOIN seal_lifecycle_event le ON le.event_id = a.installation_event_id "
            f"WHERE le.pump_tag_number = {_sql(pump_tag_number)} "
            "ORDER BY a.installation_date ASC, a.assessment_id ASC",
            self._runner,
        )


__all__ = [
    "WARRANTY_MONTHS",
    "WINDOW_STATUSES",
    "DECISION_STATUSES",
    "SealWarrantyError",
    "SealUnitNotFoundError",
    "InstallationEventNotFoundError",
    "NotAnInstallEventError",
    "InstallationEventMismatchError",
    "InspectionMismatchError",
    "InvalidChronologyError",
    "AssessmentNotFoundError",
    "AlreadyDecidedError",
    "MissingInspectionForDecisionError",
    "MissingDecisionReasonError",
    "InvalidDecisionError",
    "WarrantyWindow",
    "calculate_warranty_window",
    "create_warranty_assessment",
    "decide_assessment",
    "SealWarrantyAssessmentRepository",
]
