"""LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 -- the one
explicit adapter from GOVERNED historical installation evidence
(historical_seal_service_activity rows imported from the approved manifest)
into the record shape the frozen installation_interval_contract consumes.

Scope, by design:
  * Feeds Installation-Based MTBF ONLY (combined with installation_report).
    It is never given to current_installation_contract: Current Installation
    and Service Age stay governed solely by installation_report.
  * Only governed rows are admitted (historical_event_id present, evidence
    grade DIRECT_EVIDENCE/CORROBORATED, pump and event date set). Legacy or
    ungoverned rows in the same table are ignored.
  * Nothing is re-derived: event_date (already the approved corrected date
    when a DAY_MONTH_SWAP correction was approved), position, seal type and
    seal size are passed through verbatim. PUMP_LEVEL maps to "no structured
    seal_location", DE/NDE map to seal_location, exactly as governed reports.
  * The origin is preserved (evidence_origin) and the code is the
    historical_event_id, so a historical event is never mistaken for an
    installation_report.
"""

from __future__ import annotations

from typing import Any, Iterable

ORIGIN_INSTALLATION_REPORT = "INSTALLATION_REPORT"
ORIGIN_HISTORICAL_SERVICE_ACTIVITY = "HISTORICAL_SERVICE_ACTIVITY"
GOVERNED_EVIDENCE_GRADES = frozenset({"DIRECT_EVIDENCE", "CORROBORATED"})
_STRUCTURED_POSITIONS = frozenset({"DE", "NDE"})


def is_governed_historical_row(row: dict[str, Any]) -> bool:
    return bool(
        row.get("historical_event_id")
        and row.get("evidence_grade") in GOVERNED_EVIDENCE_GRADES
        and row.get("pump_tag_number")
        and row.get("event_date")
    )


def historical_row_to_interval_record(row: dict[str, Any]) -> dict[str, Any]:
    event_date = row["event_date"]
    if not isinstance(event_date, str):
        event_date = event_date.isoformat()
    position = row.get("position")
    return {
        "installation_code": row["historical_event_id"],
        "report_date": event_date[:10],
        "pump_tag_number": row["pump_tag_number"],
        "seal_type": row.get("seal_type"),
        "seal_size": row.get("seal_size"),
        "seal_location": position if position in _STRUCTURED_POSITIONS else None,
        "seal_code": None,
        "seal_unit_id": None,
        "source_document_name": (
            f"{row.get('source_filename')} / {row.get('source_worksheet')} / R{row.get('source_row')}"
        ),
        "event_type": row.get("event_type"),
        "evidence_origin": ORIGIN_HISTORICAL_SERVICE_ACTIVITY,
    }


def combined_installation_evidence(
    installation_reports: Iterable[dict[str, Any]], historical_rows: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """installation_report rows (unchanged, tagged with their origin) plus the
    governed historical rows adapted above. MTBF input only."""
    combined = [{**report, "evidence_origin": ORIGIN_INSTALLATION_REPORT} for report in installation_reports]
    combined.extend(historical_row_to_interval_record(row) for row in historical_rows if is_governed_historical_row(row))
    return combined


__all__ = [
    "GOVERNED_EVIDENCE_GRADES",
    "ORIGIN_HISTORICAL_SERVICE_ACTIVITY",
    "ORIGIN_INSTALLATION_REPORT",
    "combined_installation_evidence",
    "historical_row_to_interval_record",
    "is_governed_historical_row",
]
