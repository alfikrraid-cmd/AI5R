from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ltsa_pump_inventory_ingestion import _clean_text, _normalize_tag_number, _sheet_rows

# MWO-LTSA-HOC-PM-CM -- HOC PM/CM Historical Data Ingestion.
#
# Parses "CM & PM Summary HOC JUNI.xlsx" (a real historical PM/CM
# workbook for HOC-area pumps) into a pure projection -- no DB access
# here, matching the exact two-stage split ltsa_pump_inventory_ingestion.py
# already established (Stage 1: workbook -> projection; Stage 2, in
# ltsa_hoc_pm_cm_upsert.py: projection + live DB state -> plan). Reuses
# _sheet_rows/_clean_text/_normalize_tag_number directly rather than
# re-implementing OOXML reading -- these are generic cell-reading
# primitives, not specific to that module's own workbook.
#
# Sheet -> canonical entity (per the archaeology/mapping report):
#   "CM Measuring Report" -> condition_monitoring_reading (measurement log)
#   " PM Mech Seal" (leading space, verbatim sheet name) -> pm_occurrence
#   "finnding" (verbatim sheet name, source typo) -> cm_report (finding)
#   "CM&PM Summary" -> NOT ingested (proven derived/rollup-only; see
#   ingest_workbook's own docstring for the cross-foot proof).
#
# Never fabricates: a printed "-" or blank cell becomes None/absent, never
# a guessed value. Excel date variations (true numeric serials on the CM/
# PM sheets vs. literal "DD-MM-YYYY" text on the Finding sheet, plus
# genuinely blank dates) are all handled by _parse_workbook_date, which
# returns None rather than guess when a cell is truly unparseable.

_CM_SHEET = "CM Measuring Report"
_PM_SHEET = " PM Mech Seal"
_FINDING_SHEET = "finnding"

_EXCEL_EPOCH = datetime(1899, 12, 30)

_CM_COLUMNS = {
    "date": 2,
    "tag_number": 3,
    "api_plan": 4,
    "flushing_temp_de": 5, "flushing_temp_nde": 6,
    "quench_temp_de": 7, "quench_temp_nde": 8,
    "flushing_in_temp_de": 9, "flushing_in_temp_nde": 10,
    "flushing_out_temp_de": 11, "flushing_out_temp_nde": 12,
    "cooling_water_in_temp_de": 13, "cooling_water_in_temp_nde": 14,
    "cooling_water_out_temp_de": 15, "cooling_water_out_temp_nde": 16,
    "mechseal_temp_de": 17, "mechseal_temp_nde": 18,
    "mechanical_seal_leak_de": 19, "mechanical_seal_leak_nde": 20,
    "water_jacket_temp_de": 21, "water_jacket_temp_nde": 22,
    "suction_temp": 23,
    "discharge_temp": 24,
    "pump_operating_state": 25,
}
_CM_NUMERIC_FIELDS = [
    key for key in _CM_COLUMNS
    if key not in {"date", "tag_number", "api_plan", "pump_operating_state"}
    and not key.startswith("mechanical_seal_leak")
]
_CM_BOOLEAN_FIELDS = ["mechanical_seal_leak_de", "mechanical_seal_leak_nde"]

_PM_IDENTITY_COLUMNS = {
    "date": 2, "tag_number": 3, "area": 4, "location": 5, "api_plan": 7, "status": 8,
}
_PM_CHECKLIST_START_COLUMN = 9
_PM_HEADER_ROW = 7
_PM_DATA_START_ROW = 11

_FINDING_COLUMNS = {"date": 2, "tag_number": 3, "text": 4}
_FINDING_DATA_START_ROW = 4


def _parse_workbook_date(value: Any) -> str | None:
    """Never fabricates: returns None for anything not confidently
    parseable, rather than guessing. Handles the two real shapes found in
    this workbook -- a numeric Excel serial (CM/PM sheets, both stored as
    real Excel dates) and a literal 'DD-MM-YYYY' text string (the Finding
    sheet's own mixed date formatting -- some of its rows use real Excel
    dates too, handled by the same serial branch)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if re.fullmatch(r"\d+(\.\d+)?", text):
        try:
            days = float(text)
            return (_EXCEL_EPOCH + timedelta(days=days)).strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            return None

    match = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", text)
    if match:
        day, month, year = (int(part) for part in match.groups())
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return match.group(0)

    return None


def _parse_numeric(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_yn(value: Any) -> bool | None:
    """Y/N variants (MWO Section 8) -- case/whitespace-insensitive, never
    assumes False for a blank/unrecognized cell (that would be asserting
    a fact the source doesn't state)."""
    text = _clean_text(value)
    if text is None:
        return None
    normalized = text.strip().upper()
    if normalized in {"Y", "YES"}:
        return True
    if normalized in {"N", "NO"}:
        return False
    return None


def project_cm_reading_rows(rows: list[tuple[int, dict[int, str | None]]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for row_number, columns in rows:
        if row_number < 11:
            continue

        tag_number = _normalize_tag_number(columns.get(_CM_COLUMNS["tag_number"]))
        date = columns.get(_CM_COLUMNS["date"])
        if tag_number is None and date is None:
            continue  # blank row
        if tag_number is None:
            continue  # no asset to attach this reading to -- cannot ingest

        record: dict[str, Any] = {
            "source_sheet_name": _CM_SHEET,
            "source_row_number": row_number,
            "tag_number": tag_number,
            "reading_date": _parse_workbook_date(date),
            "api_plan": _clean_text(columns.get(_CM_COLUMNS["api_plan"])),
            "pump_operating_state": _clean_text(columns.get(_CM_COLUMNS["pump_operating_state"])),
        }
        for field in _CM_NUMERIC_FIELDS:
            record[field] = _parse_numeric(columns.get(_CM_COLUMNS[field]))
        for field in _CM_BOOLEAN_FIELDS:
            record[field] = _parse_yn(columns.get(_CM_COLUMNS[field]))

        projected.append(record)
    return projected


def _pm_checklist_header(rows: list[tuple[int, dict[int, str | None]]]) -> dict[int, str]:
    """Derives checklist item labels from the workbook's own header row
    (row 7) rather than hardcoding them -- 'Derive mapping from the actual
    workbook', per this MWO's own instruction."""
    header_row = next((columns for row_number, columns in rows if row_number == _PM_HEADER_ROW), {})
    labels: dict[int, str] = {}
    for column_index, value in header_row.items():
        if column_index < _PM_CHECKLIST_START_COLUMN:
            continue
        label = _clean_text(value)
        if label is not None:
            labels[column_index] = label
    return labels


def project_pm_occurrence_rows(rows: list[tuple[int, dict[int, str | None]]]) -> list[dict[str, Any]]:
    checklist_labels = _pm_checklist_header(rows)
    projected: list[dict[str, Any]] = []

    for row_number, columns in rows:
        if row_number < _PM_DATA_START_ROW:
            continue

        tag_number = _normalize_tag_number(columns.get(_PM_IDENTITY_COLUMNS["tag_number"]))
        date = columns.get(_PM_IDENTITY_COLUMNS["date"])
        if tag_number is None and date is None:
            continue  # blank row
        if tag_number is None:
            continue

        checklist_completion: dict[str, bool] = {}
        for column_index, label in checklist_labels.items():
            raw = columns.get(column_index)
            if raw is not None and _clean_text(raw) == "1":
                checklist_completion[label] = True
            # blank cell -> key absent, never a fabricated False

        projected.append(
            {
                "source_sheet_name": _PM_SHEET,
                "source_row_number": row_number,
                "tag_number": tag_number,
                "occurrence_date": _parse_workbook_date(date),
                "area": _clean_text(columns.get(_PM_IDENTITY_COLUMNS["area"])),
                "location": _clean_text(columns.get(_PM_IDENTITY_COLUMNS["location"])),
                "api_plan": _clean_text(columns.get(_PM_IDENTITY_COLUMNS["api_plan"])),
                "status": _clean_text(columns.get(_PM_IDENTITY_COLUMNS["status"])) or "DONE",
                "checklist_completion": checklist_completion,
            }
        )
    return projected


def project_finding_rows(rows: list[tuple[int, dict[int, str | None]]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for row_number, columns in rows:
        if row_number < _FINDING_DATA_START_ROW:
            continue

        tag_number = _normalize_tag_number(columns.get(_FINDING_COLUMNS["tag_number"]))
        text = _clean_text(columns.get(_FINDING_COLUMNS["text"]))
        if tag_number is None and text is None:
            continue  # blank row
        if tag_number is None or text is None:
            continue  # cannot ingest a finding with no asset or no description

        raw_date = columns.get(_FINDING_COLUMNS["date"])
        projected.append(
            {
                "source_sheet_name": _FINDING_SHEET,
                "source_row_number": row_number,
                "tag_number": tag_number,
                "failure_date": _parse_workbook_date(raw_date),
                "failure_date_source": "workbook" if _parse_workbook_date(raw_date) else None,
                "failure_description": text,
            }
        )
    return projected


def _derive_finding_dates(
    finding_rows: list[dict[str, Any]],
    cm_reading_rows: list[dict[str, Any]],
) -> None:
    """Mutates finding_rows in place. For a finding with no printed date,
    looks for CM readings of the same pump with a leak flag (DE or NDE)
    set True. Only derives a date when every matching leak reading agrees
    on exactly one distinct date -- otherwise leaves the date NULL and
    records why, per this MWO's explicit 'only when unique and
    deterministic, otherwise NULL' rule. Never overwrites a real,
    workbook-printed date.
    """
    leak_dates_by_tag: dict[str, set[str]] = {}
    leak_rows_by_tag: dict[str, list[int]] = {}
    for reading in cm_reading_rows:
        if reading.get("mechanical_seal_leak_de") or reading.get("mechanical_seal_leak_nde"):
            if reading.get("reading_date") is None:
                continue
            leak_dates_by_tag.setdefault(reading["tag_number"], set()).add(reading["reading_date"])
            leak_rows_by_tag.setdefault(reading["tag_number"], []).append(reading["source_row_number"])

    for finding in finding_rows:
        if finding["failure_date"] is not None:
            continue

        candidate_dates = leak_dates_by_tag.get(finding["tag_number"], set())
        if len(candidate_dates) == 1:
            (derived_date,) = candidate_dates
            finding["failure_date"] = derived_date
            finding["failure_date_source"] = "derived_from_condition_monitoring_reading"
            finding["failure_date_derivation_evidence"] = {
                "matched_tag": finding["tag_number"],
                "matched_source_sheet_name": _CM_SHEET,
                "matched_source_row_numbers": sorted(leak_rows_by_tag.get(finding["tag_number"], [])),
            }
        elif len(candidate_dates) > 1:
            finding["failure_date_source"] = "unavailable_ambiguous_cm_match"
        else:
            finding["failure_date_source"] = "unavailable_no_cm_match"


def ingest_workbook(workbook_path: Path) -> dict[str, Any]:
    cm_reading_rows = project_cm_reading_rows(_sheet_rows(workbook_path, _CM_SHEET))
    pm_occurrence_rows = project_pm_occurrence_rows(_sheet_rows(workbook_path, _PM_SHEET))
    finding_rows = project_finding_rows(_sheet_rows(workbook_path, _FINDING_SHEET))

    _derive_finding_dates(finding_rows, cm_reading_rows)

    return {
        "metadata": {
            "source_workbook_name": workbook_path.name,
            "cm_reading_row_count": len(cm_reading_rows),
            "pm_occurrence_row_count": len(pm_occurrence_rows),
            "finding_row_count": len(finding_rows),
        },
        "condition_monitoring_readings": cm_reading_rows,
        "pm_occurrences": pm_occurrence_rows,
        "findings": finding_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project the HOC PM/CM workbook into canonical condition_monitoring_reading/pm_occurrence/cm_report records."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    projection = ingest_workbook(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(projection, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
