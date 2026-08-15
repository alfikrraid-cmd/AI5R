from __future__ import annotations

import hashlib
from typing import Any

# MWO-LTSA-HOC-PM-CM -- HOC PM/CM Historical Data Ingestion, Stage 2.
#
# Pure reconciliation: projection (Stage 1, ltsa_hoc_pm_cm_ingestion.py) +
# live DB state -> plan (insert/unchanged/rejected per entity). No I/O
# here -- mirrors ltsa_pump_inventory_db_upsert.py::plan_import's own
# pure-function shape exactly, so this is testable without a database.
#
# Identity strategy: every code is a deterministic SHA1 of
# (source_sheet_name, source_row_number) -- same content-hash convention
# ltsa_internal_component_ingestion.py::build_internal_component_stock_id
# already established. Re-importing the same workbook always recomputes
# the same codes, so a second import is naturally idempotent as long as
# "code already exists" is treated as "unchanged" (see NEVER_OVERWRITE
# below) rather than triggering an update.
#
# NEVER_OVERWRITE: unlike ltsa_pump_inventory_db_upsert.py's pump/seal
# merge (which blank-fills existing rows), pm_occurrence/
# condition_monitoring_reading/cm_report are historical, append-only
# records (their own Gateways are already create/detail/list only, no
# update endpoint -- see CORE-SERVICES/API/pm_occurrence_gateway.py /
# condition_monitoring_reading_gateway.py). Per this MWO's explicit
# instruction, a row whose deterministic code already exists is always
# "unchanged", never patched -- there is no update path for these three
# entities in this ingestion, by design.
#
# Pump resolution: never creates a pump. A row whose tag_number does not
# resolve against state["pumps"] is rejected and reported, never silently
# dropped and never given a synthetic pump row.


def build_condition_monitoring_reading_code(source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-CMONR-{digest}"


def build_pm_occurrence_code(source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-PMO-{digest}"


def build_cm_report_finding_code(source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-CMF-{digest}"


def build_unscheduled_reference(source_workbook_name: str) -> str:
    """Deterministic, disclosed placeholder for pm_schedule_code /
    condition_monitoring_schedule_code -- both are required (NOT NULL) but
    informal, non-FK-enforced references (see pm_occurrence/
    condition_monitoring_reading DDL comments in CANONICAL_SCHEMA.sql), and
    this workbook carries no separate PM/CM plan sheet to derive a real
    schedule from. The literal "UNSCHEDULED" substring makes this
    self-disclosing in any query result -- never a fabricated schedule
    row, never inserted into pm_schedule/condition_monitoring_schedule."""
    return f"UNSCHEDULED::{source_workbook_name}"


def _pump_tags(state: dict[str, list[dict[str, Any]]]) -> set[str]:
    return {row["tag_number"] for row in state.get("pumps", [])}


def plan_import(projection: dict[str, Any], state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    known_pump_tags = _pump_tags(state)
    source_workbook_name = projection["metadata"]["source_workbook_name"]
    unscheduled_reference = build_unscheduled_reference(source_workbook_name)

    existing_cm_reading_codes = {row["condition_monitoring_reading_code"] for row in state.get("condition_monitoring_readings", [])}
    existing_pm_occurrence_codes = {row["pm_occurrence_code"] for row in state.get("pm_occurrences", [])}
    existing_cm_report_codes = {row["cm_report_code"] for row in state.get("cm_reports", [])}

    plan: dict[str, Any] = {
        "condition_monitoring_readings": {"insert": [], "unchanged": [], "rejected": []},
        "pm_occurrences": {"insert": [], "unchanged": [], "rejected": []},
        "findings": {"insert": [], "unchanged": [], "rejected": []},
        "unresolved_pump_tags": {},
    }

    for row in projection["condition_monitoring_readings"]:
        code = build_condition_monitoring_reading_code(row["source_sheet_name"], row["source_row_number"])
        if row["tag_number"] not in known_pump_tags:
            plan["condition_monitoring_readings"]["rejected"].append(
                {
                    "condition_monitoring_reading_code": code,
                    "tag_number": row["tag_number"],
                    "source_sheet_name": row["source_sheet_name"],
                    "source_row_number": row["source_row_number"],
                    "reason": "pump tag not found in canonical ltsa_pumps",
                }
            )
            plan["unresolved_pump_tags"].setdefault(row["tag_number"], []).append(
                f"{row['source_sheet_name']}!row{row['source_row_number']}"
            )
            continue

        if code in existing_cm_reading_codes:
            plan["condition_monitoring_readings"]["unchanged"].append(code)
            continue

        plan["condition_monitoring_readings"]["insert"].append(
            {
                "condition_monitoring_reading_code": code,
                "condition_monitoring_schedule_code": unscheduled_reference,
                "asset_code": row["tag_number"],
                "asset_type": "PUMP",
                "reading_date": row["reading_date"],
                "flushing_temp_de": row["flushing_temp_de"], "flushing_temp_nde": row["flushing_temp_nde"],
                "quench_temp_de": row["quench_temp_de"], "quench_temp_nde": row["quench_temp_nde"],
                "flushing_in_temp_de": row["flushing_in_temp_de"], "flushing_in_temp_nde": row["flushing_in_temp_nde"],
                "flushing_out_temp_de": row["flushing_out_temp_de"], "flushing_out_temp_nde": row["flushing_out_temp_nde"],
                "cooling_water_in_temp_de": row["cooling_water_in_temp_de"], "cooling_water_in_temp_nde": row["cooling_water_in_temp_nde"],
                "cooling_water_out_temp_de": row["cooling_water_out_temp_de"], "cooling_water_out_temp_nde": row["cooling_water_out_temp_nde"],
                "mechseal_temp_de": row["mechseal_temp_de"], "mechseal_temp_nde": row["mechseal_temp_nde"],
                "mechanical_seal_leak_de": row["mechanical_seal_leak_de"], "mechanical_seal_leak_nde": row["mechanical_seal_leak_nde"],
                "water_jacket_temp_de": row["water_jacket_temp_de"], "water_jacket_temp_nde": row["water_jacket_temp_nde"],
                "suction_temp": row["suction_temp"],
                "discharge_temp": row["discharge_temp"],
                "pump_operating_state": row["pump_operating_state"],
                "source_workbook_name": source_workbook_name,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
            }
        )

    for row in projection["pm_occurrences"]:
        code = build_pm_occurrence_code(row["source_sheet_name"], row["source_row_number"])
        if row["tag_number"] not in known_pump_tags:
            plan["pm_occurrences"]["rejected"].append(
                {
                    "pm_occurrence_code": code,
                    "tag_number": row["tag_number"],
                    "source_sheet_name": row["source_sheet_name"],
                    "source_row_number": row["source_row_number"],
                    "reason": "pump tag not found in canonical ltsa_pumps",
                }
            )
            plan["unresolved_pump_tags"].setdefault(row["tag_number"], []).append(
                f"{row['source_sheet_name']}!row{row['source_row_number']}"
            )
            continue

        if code in existing_pm_occurrence_codes:
            plan["pm_occurrences"]["unchanged"].append(code)
            continue

        plan["pm_occurrences"]["insert"].append(
            {
                "pm_occurrence_code": code,
                "pm_schedule_code": unscheduled_reference,
                "asset_code": row["tag_number"],
                "asset_type": "PUMP",
                "occurrence_date": row["occurrence_date"],
                "status": row["status"],
                "checklist_completion": row["checklist_completion"],
                "source_workbook_name": source_workbook_name,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
            }
        )

    for row in projection["findings"]:
        code = build_cm_report_finding_code(row["source_sheet_name"], row["source_row_number"])
        if row["tag_number"] not in known_pump_tags:
            plan["findings"]["rejected"].append(
                {
                    "cm_report_code": code,
                    "tag_number": row["tag_number"],
                    "source_sheet_name": row["source_sheet_name"],
                    "source_row_number": row["source_row_number"],
                    "reason": "pump tag not found in canonical ltsa_pumps",
                }
            )
            plan["unresolved_pump_tags"].setdefault(row["tag_number"], []).append(
                f"{row['source_sheet_name']}!row{row['source_row_number']}"
            )
            continue

        if code in existing_cm_report_codes:
            plan["findings"]["unchanged"].append(code)
            continue

        plan["findings"]["insert"].append(
            {
                "cm_report_code": code,
                "asset_code": row["tag_number"],
                "asset_type": "PUMP",
                "failure_category": "MECHANICAL_SEAL_LEAKAGE",
                "severity": "UNSPECIFIED",
                "failure_description": row["failure_description"],
                "failure_date": row["failure_date"],
                "status": "OPEN",
                "source_workbook_name": source_workbook_name,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
                "failure_date_source": row["failure_date_source"],
                "failure_date_derivation_evidence": row.get("failure_date_derivation_evidence"),
            }
        )

    plan["summary"] = {
        entity: {
            "insert": len(plan[entity]["insert"]),
            "unchanged": len(plan[entity]["unchanged"]),
            "rejected": len(plan[entity]["rejected"]),
        }
        for entity in ("condition_monitoring_readings", "pm_occurrences", "findings")
    }
    plan["unresolved_pump_tag_count"] = len(plan["unresolved_pump_tags"])
    return plan
