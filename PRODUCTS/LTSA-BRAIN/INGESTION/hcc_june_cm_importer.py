"""Dry-run planner for the HCC June CM Measuring Report.

This module deliberately has no database write path.  The caller supplies
read-only asset and occurrence state, so the plan can be reviewed before a
separately-authorized importer is allowed to persist anything.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
import re
import argparse
import hashlib
import json
import subprocess

import openpyxl


SOURCE_SHEET = "CM Measuring Report"
QUARANTINED_TAGS = {"701-MM-51", "702-MM-51"}
_FIELDS = {
    "flushing_temp_de": 5, "flushing_temp_nde": 6,
    "quench_temp_de": 7, "quench_temp_nde": 8,
    "flushing_in_temp_de": 9, "flushing_in_temp_nde": 10,
    "flushing_out_temp_de": 11, "flushing_out_temp_nde": 12,
    "cooling_water_in_temp_de": 13, "cooling_water_in_temp_nde": 14,
    "cooling_water_out_temp_de": 15, "cooling_water_out_temp_nde": 16,
    "mechseal_temp_de": 17, "mechseal_temp_nde": 18,
    "mechanical_seal_leak_de": 19, "mechanical_seal_leak_nde": 20,
    "water_jacket_temp_de": 21, "water_jacket_temp_nde": 22,
    "suction_temp": 23, "discharge_temp": 24,
}
_NUMERIC = {name for name in _FIELDS if not name.startswith("mechanical_seal_leak")}


def normalize_tag(value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return re.sub(r"\s+", "", str(value)).upper()


def parse_date(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip() if value is not None else ""
    return text[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", text) else None


def parse_number(value: Any) -> int | float | None:
    if value is None or not str(value).strip():
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def parse_leak(value: Any) -> bool | None:
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().upper()
    if normalized == "Y":
        return True
    if normalized == "N":
        return False
    return None


def parse_workbook(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook[SOURCE_SHEET]
    rows: list[dict[str, Any]] = []
    excluded = 0
    for row_number, row in enumerate(sheet.iter_rows(min_row=11, values_only=True), 11):
        tag = normalize_tag(row[2] if len(row) > 2 else None)
        reading_date = parse_date(row[1] if len(row) > 1 else None)
        if tag is None and reading_date is None:
            excluded += 1
            continue
        if tag is None or reading_date is None:
            excluded += 1
            continue
        record: dict[str, Any] = {
            "source_workbook_name": Path(path).name,
            "source_sheet_name": SOURCE_SHEET,
            "source_row_number": row_number,
            "asset_code": tag,
            "reading_date": reading_date,
            "api_plan_snapshot": str(row[3]).strip() if row[3] is not None else None,
            "pump_operating_state": str(row[24]).strip() if row[24] is not None else None,
        }
        for field, column in _FIELDS.items():
            record[field] = parse_leak(row[column - 1]) if field.startswith("mechanical_seal_leak") else parse_number(row[column - 1])
        rows.append(record)
    return rows, {"raw_rows": max(sheet.max_row - 10, 0), "eligible": len(rows), "excluded": excluded}


def plan_import(rows: list[dict[str, Any]], assets: dict[str, str | None], existing_keys: set[tuple[str, str]], existing_counts: dict[tuple[str, str], int] | None = None) -> dict[str, Any]:
    existing_counts = existing_counts or {}
    plan = {"safe_insert": [], "skip_existing": [], "block_ambiguous": [], "quarantined": [], "asset_not_found": []}
    for row in rows:
        asset_type = assets.get(row["asset_code"])
        if asset_type is None and row["asset_code"] not in assets:
            plan["asset_not_found"].append(row)
            continue
        if row["asset_code"] in QUARANTINED_TAGS or asset_type != "PUMP":
            plan["quarantined"].append({**row, "reason": "QUARANTINED_EQUIPMENT_TYPE_UNRESOLVED"})
            continue
        key = (row["asset_code"], row["reading_date"])
        if existing_counts.get(key, 0) > 1:
            plan["block_ambiguous"].append(row)
        elif key in existing_keys:
            plan["skip_existing"].append(row)
        else:
            plan["safe_insert"].append(row)
    return plan


def reading_code(row: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        f"{row['source_workbook_name']}::{row['source_sheet_name']}::{row['source_row_number']}".encode()
    ).hexdigest()[:16].upper()
    return f"LTSA-CMONR-HCCJUNE-{digest}"


def sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def apply_plan(plan: dict[str, Any], container: str = "ai5r-runtime-postgres-1") -> int:
    columns = [
        "condition_monitoring_reading_code", "condition_monitoring_schedule_code", "asset_code", "asset_type",
        "reading_date", *(_FIELDS.keys()), "pump_operating_state", "workflow_status", "provenance",
        "source_workbook_name", "source_sheet_name", "source_row_number", "api_plan_snapshot",
    ]
    statements = ["BEGIN;"]
    for row in plan["safe_insert"]:
        values = [reading_code(row), f"UNSCHEDULED::{row['source_workbook_name']}", row["asset_code"], "PUMP", row["reading_date"]]
        values.extend(row[field] for field in _FIELDS)
        values.extend([row["pump_operating_state"], "FINALIZED", "HISTORICAL_IMPORT", row["source_workbook_name"], row["source_sheet_name"], row["source_row_number"], row["api_plan_snapshot"]])
        statements.append(f"INSERT INTO condition_monitoring_reading ({', '.join(columns)}) VALUES ({', '.join(sql_value(v) for v in values)});")
    statements.append("COMMIT;")
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "ai5r", "-d", "ltsa_brain", "-v", "ON_ERROR_STOP=1"],
        input="\n".join(statements), text=True, capture_output=True,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "controlled import failed")
    return len(plan["safe_insert"])


__all__ = ["parse_workbook", "plan_import", "normalize_tag", "parse_leak"]
