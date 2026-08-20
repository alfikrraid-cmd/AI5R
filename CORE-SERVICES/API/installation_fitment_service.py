"""MWO-LTSA-SEAL-INSTALLATION-FITMENT-001 -- links an existing
installation_report row to the exact seal_lifecycle_event(INSTALL) it
documents, closing the physical-fitment chain:

    seal_unit -> seal_lifecycle_event(INSTALL) -> ltsa_pumps -> installation_report

CANONICAL PRINCIPLE (this MWO's own frozen rule): seal_lifecycle_event.
event_type='INSTALL' is the authoritative physical installation EVENT
(state/history truth); installation_report only documents that event
(engineering evidence). Warranty/lifecycle chronology always uses
INSTALL.event_at -- report_date is document metadata only, never a
competing installation-date source. No new table: installation_report
already carries seal_unit_id/pump_tag_number (migration 018); this
module only adds/reads installation_event_id (migration 022) and the
guarded link operation -- reusing seal_lifecycle_event and seal_unit
unmodified, never writing seal_unit.status/current_pump_tag_number
(that stays exclusively seal_lifecycle_service.apply_lifecycle_event's
job).

IMMUTABILITY: once installation_event_id is set on a report, it can
never be re-linked (guarded UPDATE ... WHERE installation_event_id IS
NULL) -- the smallest model preserving linkage history without a second
audit engine, the same "one guarded one-time transition" shape
seal_warranty_service.decide_assessment() already established.
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

# A curated identity/linkage subset (this MWO's own INSTALLATION REPORT
# DETAIL list), not all ~60 raw document columns -- the existing
# GET /api/ltsa/installations/{code} (n8n InstallationGateway) already
# serves the full raw-document detail; duplicating every column here
# would be a second, competing detail engine, not a fitment linkage.
_REPORT_COLUMNS = (
    "installation_code, report_no, report_date, plant_equip_no, seal_code, seal_unit_id, "
    "pump_tag_number, installation_event_id, linked_by, link_reason, source_document_name, "
    "created_at, updated_at"
)
_REPORT_COLUMNS_QUALIFIED = ", ".join(f"r.{col.strip()}" for col in _REPORT_COLUMNS.split(","))


class InstallationFitmentError(ValueError):
    pass


class InstallationReportNotFoundError(InstallationFitmentError):
    pass


class SealUnitNotFoundError(InstallationFitmentError):
    pass


class InstallationEventNotFoundError(InstallationFitmentError):
    pass


class NotAnInstallEventError(InstallationFitmentError):
    pass


class SealUnitMismatchError(InstallationFitmentError):
    pass


class PumpMismatchError(InstallationFitmentError):
    pass


class SealCodeContradictionError(InstallationFitmentError):
    pass


class AlreadyLinkedError(InstallationFitmentError):
    pass


class MissingReasonError(InstallationFitmentError):
    pass


def link_installation_report(
    runner: "DatabaseRunner",
    *,
    installation_code: str,
    seal_unit_id: str,
    installation_event_id: str,
    pump_tag_number: str,
    reason: str,
    linked_by: str,
) -> dict:
    """Guarded, atomic, one-time link. Every contradiction is checked
    against immutable, already-append-only facts (seal_lifecycle_event
    rows never change after creation -- #6.2's own discipline) via a
    plain read before the guarded write, the same "read-then-guarded-
    write" pattern seal_warranty_service.create_warranty_assessment()
    already established -- no race a concurrent mutation could exploit,
    since nothing read here is ever updated in place except the report's
    OWN installation_event_id, which the write's own guard protects."""
    if not (reason or "").strip():
        raise MissingReasonError("reason is required to link an installation report")
    if not is_valid_uuid(seal_unit_id):
        raise SealUnitNotFoundError(seal_unit_id)
    if not is_valid_uuid(installation_event_id):
        raise InstallationEventNotFoundError(installation_event_id)

    report_rows = _json_query(
        f"SELECT installation_code, seal_unit_id, pump_tag_number, seal_code, installation_event_id "
        f"FROM installation_report WHERE installation_code = {_sql(installation_code)}",
        runner,
    )
    if not report_rows:
        raise InstallationReportNotFoundError(installation_code)
    report = report_rows[0]
    if report["installation_event_id"] is not None:
        raise AlreadyLinkedError(f"installation_report {installation_code!r} is already linked")
    if report["seal_unit_id"] is not None and report["seal_unit_id"] != seal_unit_id:
        raise SealUnitMismatchError(
            f"report already carries seal_unit_id {report['seal_unit_id']!r}, cannot relink to {seal_unit_id!r}"
        )
    if report["pump_tag_number"] is not None and report["pump_tag_number"] != pump_tag_number:
        raise PumpMismatchError(
            f"report already carries pump_tag_number {report['pump_tag_number']!r}, cannot relink to {pump_tag_number!r}"
        )

    unit_rows = _json_query(f"SELECT seal_unit_id, seal_code FROM seal_unit WHERE seal_unit_id = {_sql(seal_unit_id)}", runner)
    if not unit_rows:
        raise SealUnitNotFoundError(seal_unit_id)
    seal_unit = unit_rows[0]

    if report["seal_code"] is not None and report["seal_code"] != seal_unit["seal_code"]:
        raise SealCodeContradictionError(
            f"report.seal_code {report['seal_code']!r} contradicts seal_unit.seal_code {seal_unit['seal_code']!r}"
        )

    event_rows = _json_query(
        f"SELECT event_id, seal_unit_id, event_type, pump_tag_number FROM seal_lifecycle_event "
        f"WHERE event_id = {_sql(installation_event_id)}",
        runner,
    )
    if not event_rows:
        raise InstallationEventNotFoundError(installation_event_id)
    event = event_rows[0]
    if event["event_type"] != "INSTALL":
        raise NotAnInstallEventError(installation_event_id)
    if event["seal_unit_id"] != seal_unit_id:
        raise SealUnitMismatchError(
            f"installation_event {installation_event_id!r} belongs to seal_unit {event['seal_unit_id']!r}, not {seal_unit_id!r}"
        )
    if event["pump_tag_number"] != pump_tag_number:
        raise PumpMismatchError(
            f"installation_event {installation_event_id!r} is on pump {event['pump_tag_number']!r}, not {pump_tag_number!r}"
        )

    script = f"""
WITH unlinked AS (
    SELECT installation_code FROM installation_report
    WHERE installation_code = {_sql(installation_code)} AND installation_event_id IS NULL
),
linked_upd AS (
    UPDATE installation_report SET
        seal_unit_id = {_sql(seal_unit_id)},
        pump_tag_number = {_sql(pump_tag_number)},
        installation_event_id = {_sql(installation_event_id)},
        linked_by = {_sql(linked_by)},
        link_reason = {_sql(reason)},
        updated_at = NOW()
    WHERE installation_code IN (SELECT installation_code FROM unlinked)
    RETURNING {_REPORT_COLUMNS}
)
SELECT COALESCE((SELECT json_agg(row_to_json(l))::text FROM linked_upd l), '[]');
"""
    raw = runner.query_scalar(script.strip())
    rows = json.loads(raw or "[]")
    if not rows:
        # Guard failed between the plain reads above and this write -- a
        # genuinely concurrent link attempt won the race.
        raise AlreadyLinkedError(f"installation_report {installation_code!r} is already linked")
    return rows[0]


class InstallationReportFitmentRepository:
    """Read-only from outside this module: find/list by the new
    structured linkage dimensions. No update()/delete() method exists --
    the only mutation path anywhere is link_installation_report()'s own
    single guarded one-time transition."""

    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_by_code(self, installation_code: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_REPORT_COLUMNS_QUALIFIED}, le.event_at AS installation_event_at "
            "FROM installation_report r "
            "LEFT JOIN seal_lifecycle_event le ON le.event_id = r.installation_event_id "
            f"WHERE r.installation_code = {_sql(installation_code)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_by_seal_unit(self, seal_unit_id: str) -> list[dict]:
        if not is_valid_uuid(seal_unit_id):
            return []
        return _json_query(
            f"SELECT {_REPORT_COLUMNS_QUALIFIED}, le.event_at AS installation_event_at "
            "FROM installation_report r "
            "LEFT JOIN seal_lifecycle_event le ON le.event_id = r.installation_event_id "
            f"WHERE r.seal_unit_id = {_sql(seal_unit_id)} "
            "ORDER BY le.event_at ASC NULLS LAST, r.installation_code ASC",
            self._runner,
        )

    def list_by_pump(self, pump_tag_number: str) -> list[dict]:
        return _json_query(
            f"SELECT {_REPORT_COLUMNS_QUALIFIED}, le.event_at AS installation_event_at "
            "FROM installation_report r "
            "LEFT JOIN seal_lifecycle_event le ON le.event_id = r.installation_event_id "
            f"WHERE r.pump_tag_number = {_sql(pump_tag_number)} "
            "ORDER BY le.event_at ASC NULLS LAST, r.installation_code ASC",
            self._runner,
        )

    def list_by_installation_event(self, installation_event_id: str) -> list[dict]:
        if not is_valid_uuid(installation_event_id):
            return []
        return _json_query(
            f"SELECT {_REPORT_COLUMNS_QUALIFIED}, le.event_at AS installation_event_at "
            "FROM installation_report r "
            "LEFT JOIN seal_lifecycle_event le ON le.event_id = r.installation_event_id "
            f"WHERE r.installation_event_id = {_sql(installation_event_id)} "
            "ORDER BY r.installation_code ASC",
            self._runner,
        )


__all__ = [
    "InstallationFitmentError",
    "InstallationReportNotFoundError",
    "SealUnitNotFoundError",
    "InstallationEventNotFoundError",
    "NotAnInstallEventError",
    "SealUnitMismatchError",
    "PumpMismatchError",
    "SealCodeContradictionError",
    "AlreadyLinkedError",
    "MissingReasonError",
    "link_installation_report",
    "InstallationReportFitmentRepository",
]
