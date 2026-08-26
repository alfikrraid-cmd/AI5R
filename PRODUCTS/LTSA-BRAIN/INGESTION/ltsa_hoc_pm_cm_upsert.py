from __future__ import annotations

import hashlib
import re
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
    """LEGACY (V1). Never called by plan_import() anymore (see V2 below) --
    kept, unchanged, only because it is the exact function that produced
    every already-imported June row's real, permanent identity. Existing
    production rows are never regenerated or rewritten (MWO-LTSA-PM-CMON-
    DETERMINISTIC-ID-FIX-015B1's own explicit rule)."""
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-CMONR-{digest}"


def build_pm_occurrence_code(source_sheet_name: str, source_row_number: int) -> str:
    """LEGACY (V1). See build_condition_monitoring_reading_code's own note --
    identical reasoning."""
    digest = hashlib.sha1(f"{source_sheet_name}::{source_row_number}".encode("utf-8")).hexdigest()[:16].upper()
    return f"LTSA-PMO-{digest}"


# MWO-LTSA-PM-CMON-DETERMINISTIC-ID-FIX-015B1 -- V1's hash input
# (source_sheet_name + source_row_number only) silently collides across
# DIFFERENT workbooks/months that share the same template sheet names and
# row numbers (confirmed: January " PM Mech Seal" row 11 hashes identically
# to June's already-imported row 11, even though they are different pumps
# on different dates). V2 folds the source workbook's own identity into
# the hash so two different workbooks can never collide, and uses a
# distinct code PREFIX so a V2 code can never be string-equal to any V1
# code even in a theoretical residual hash collision. Legacy V1 rows are
# never regenerated, renamed, or migrated -- V2 governs NEW imports only.


def normalize_source_workbook_name(raw: str) -> str:
    """Deterministic, host/OS-independent workbook identity: the filename
    only, never a directory path. Splits on BOTH \\ and / explicitly --
    os.path.basename() is NOT enough here, because it only recognizes the
    CURRENT host's own separator convention (posixpath.basename does not
    split on backslashes at all), so a Windows absolute path and a Linux
    absolute path for the exact same file would otherwise normalize to two
    DIFFERENT identities depending only on which machine ran the code.
    Never fabricates: a value with no separator at all is returned as-is
    (already just a filename)."""
    text = str(raw).strip()
    segments = re.split(r"[\\/]+", text)
    name = segments[-1] if segments else text
    return name.strip()


def build_pm_occurrence_code_v2(normalized_workbook: str, source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(
        f"{normalized_workbook}::{source_sheet_name}::{source_row_number}".encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"LTSA-PMO2-{digest}"


def build_condition_monitoring_reading_code_v2(normalized_workbook: str, source_sheet_name: str, source_row_number: int) -> str:
    digest = hashlib.sha1(
        f"{normalized_workbook}::{source_sheet_name}::{source_row_number}".encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"LTSA-CMONR2-{digest}"


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
    # MWO-LTSA-PM-CMON-DETERMINISTIC-ID-FIX-015B1 -- normalized once, used
    # everywhere below (schedule placeholder, V2 code hash input, and the
    # source_workbook_name stored on every new insert) so a single import
    # run is internally consistent regardless of which OS/path shape the
    # caller supplied the workbook as.
    normalized_workbook = normalize_source_workbook_name(source_workbook_name)
    unscheduled_reference = build_unscheduled_reference(normalized_workbook)

    existing_cm_reading_codes = {row["condition_monitoring_reading_code"] for row in state.get("condition_monitoring_readings", [])}
    existing_pm_occurrence_codes = {row["pm_occurrence_code"] for row in state.get("pm_occurrences", [])}
    existing_cm_report_codes = {row["cm_report_code"] for row in state.get("cm_reports", [])}

    # Collision guard for V2 imports: when a NEWLY generated code happens
    # to already exist, check the EXISTING row's own recorded provenance
    # (per this MWO's own explicit "verify duplicate identity using source
    # provenance" rule) before trusting code-equality alone. Two safe
    # outcomes collapse to "unchanged" (true replay): the existing row's
    # provenance genuinely matches this source row, OR the existing row
    # has no provenance recorded at all (a legacy/narrower load_state()
    # shape -- exactly V1's own original "code equality is enough" trust,
    # never a false collision just because provenance data happens to be
    # unavailable). Only a RECORDED, DIFFERING provenance is a genuine
    # collision -- reported, never silently skipped.
    existing_cm_reading_provenance_by_code = {
        row["condition_monitoring_reading_code"]: (row.get("source_workbook_name"), row.get("source_sheet_name"), row.get("source_row_number"))
        for row in state.get("condition_monitoring_readings", [])
    }
    existing_pm_occurrence_provenance_by_code = {
        row["pm_occurrence_code"]: (row.get("source_workbook_name"), row.get("source_sheet_name"), row.get("source_row_number"))
        for row in state.get("pm_occurrences", [])
    }

    plan: dict[str, Any] = {
        "condition_monitoring_readings": {"insert": [], "unchanged": [], "rejected": []},
        "pm_occurrences": {"insert": [], "unchanged": [], "rejected": []},
        "findings": {"insert": [], "unchanged": [], "rejected": []},
        "collisions": {"condition_monitoring_readings": [], "pm_occurrences": []},
        "unresolved_pump_tags": {},
    }

    for row in projection["condition_monitoring_readings"]:
        code = build_condition_monitoring_reading_code_v2(normalized_workbook, row["source_sheet_name"], row["source_row_number"])
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
            # Same generated code already exists. Trust it as an
            # idempotent replay ("unchanged") UNLESS the existing row has
            # its own provenance recorded AND that provenance names a
            # DIFFERENT source row -- only that is a genuine collision. No
            # provenance recorded on the existing row (legacy/narrower
            # state) is never treated as a collision -- that would be a
            # false positive purely from missing data, not evidence.
            existing_provenance = existing_cm_reading_provenance_by_code.get(code)
            this_provenance = (normalized_workbook, row["source_sheet_name"], row["source_row_number"])
            if existing_provenance is None or existing_provenance[0] is None or existing_provenance == this_provenance:
                plan["condition_monitoring_readings"]["unchanged"].append(code)
            else:
                plan["collisions"]["condition_monitoring_readings"].append(
                    {
                        "condition_monitoring_reading_code": code,
                        "tag_number": row["tag_number"],
                        "source_workbook_name": normalized_workbook,
                        "source_sheet_name": row["source_sheet_name"],
                        "source_row_number": row["source_row_number"],
                        "existing_provenance": existing_provenance,
                    }
                )
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
                "source_workbook_name": normalized_workbook,
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
            }
        )

    for row in projection["pm_occurrences"]:
        code = build_pm_occurrence_code_v2(normalized_workbook, row["source_sheet_name"], row["source_row_number"])
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
            existing_provenance = existing_pm_occurrence_provenance_by_code.get(code)
            this_provenance = (normalized_workbook, row["source_sheet_name"], row["source_row_number"])
            if existing_provenance is None or existing_provenance[0] is None or existing_provenance == this_provenance:
                plan["pm_occurrences"]["unchanged"].append(code)
            else:
                plan["collisions"]["pm_occurrences"].append(
                    {
                        "pm_occurrence_code": code,
                        "tag_number": row["tag_number"],
                        "source_workbook_name": normalized_workbook,
                        "source_sheet_name": row["source_sheet_name"],
                        "source_row_number": row["source_row_number"],
                        "existing_provenance": existing_provenance,
                    }
                )
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
                "source_workbook_name": normalized_workbook,
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
    for entity in ("condition_monitoring_readings", "pm_occurrences"):
        plan["summary"][entity]["collisions"] = len(plan["collisions"][entity])
    plan["unresolved_pump_tag_count"] = len(plan["unresolved_pump_tags"])
    plan["collision_count"] = len(plan["collisions"]["condition_monitoring_readings"]) + len(plan["collisions"]["pm_occurrences"])
    return plan
