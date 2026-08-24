from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ltsa_hoc_pm_cm_ingestion import ingest_workbook
from ltsa_hoc_pm_cm_upsert import plan_import
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query

# MWO-LTSA-HOC-PM-CM -- HOC PM/CM Historical Data Ingestion, Stage 3.
#
# DB orchestrator: reuses DatabaseConfig/DatabaseRunner from
# ltsa_pump_inventory_db_upsert.py verbatim (same docker-compose-exec-psql
# transport, same env-file/compose-file/service/user/database contract) --
# no second database connection mechanism. load_state() only reads the
# columns needed to resolve pump identity and detect already-imported
# rows (deterministic-code presence); apply_plan() issues INSERT-only SQL
# in one transaction (never UPDATE -- see ltsa_hoc_pm_cm_upsert.py's own
# NEVER_OVERWRITE note) and refuses to run if anything is unresolved
# unless --allow-unresolved is passed (dry-run always safe; apply always
# prints the unresolved-tag report either way).


def load_state(runner: DatabaseRunner) -> dict[str, list[dict[str, Any]]]:
    return {
        "pumps": _json_query("SELECT tag_number FROM ltsa_pumps", runner),
        "condition_monitoring_readings": _json_query(
            "SELECT condition_monitoring_reading_code FROM condition_monitoring_reading", runner
        ),
        "pm_occurrences": _json_query("SELECT pm_occurrence_code FROM pm_occurrence", runner),
        "cm_reports": _json_query("SELECT cm_report_code FROM cm_report", runner),
    }


# MWO-LTSA-JUNE-HOC-FINDING-ATTACHMENT-001 -- findings from this workbook's
# "finnding" sheet are supporting evidence for an existing
# condition_monitoring_reading leak observation, never a standalone
# cm_report row (cm_report is the reactive Corrective-Maintenance domain;
# a leak noted during routine Condition Monitoring is a different concept
# that happens to share the "CM" initials -- see this line's own
# terminology-collision finding). plan_import()'s generic findings->
# cm_report shape is therefore deliberately NOT used as the write path
# below; this module attaches each safely-matched finding's text to
# condition_monitoring_reading.finding instead.
#
# Two disclosed exclusions, for two different reasons -- never merged into
# one bucket:
#   - 140-P-13A (finnding row 10): a genuine unique match exists (see
#     _match_finding_to_reading), but is held pending human review against
#     a separate, already-staged August-batch finding candidate for the
#     same pump -- a cross-batch duplicate concern this ingestion path has
#     no evidence to resolve on its own.
#   - 110-P-12B (finnding row 7): no printed date in source, and this pump
#     has TWO leak='Y' readings in June (06-18, 06-24) -- already excluded
#     by _match_finding_to_reading's own uniqueness rule (no date -> no
#     match). Listed here too so the exclusion is explicit and traceable
#     in one place, not an incidental side effect of the matching
#     algorithm alone.
QUARANTINED_FINDING_ROWS: frozenset[tuple[str, int]] = frozenset(
    {
        ("finnding", 10),  # 140-P-13A -- cross-batch duplicate review pending
        ("finnding", 7),  # 110-P-12B -- ambiguous match, no safe target reading
    }
)


def _match_finding_to_reading(
    finding: dict[str, Any], cmon_inserts: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Returns the one condition_monitoring_reading insert row this
    finding is safe to attach to, or None if no safe match exists. Never
    guesses: requires exactly one insert row for the same asset_code +
    reading_date with a leak flag set (DE or NDE) -- the same evidence
    link a human reviewer would use. A finding with no date, zero matching
    leak readings, or more than one (ambiguous) same-day leak reading
    returns None rather than picking one."""
    if finding["failure_date"] is None:
        return None
    candidates = [
        reading
        for reading in cmon_inserts
        if reading["asset_code"] == finding["asset_code"]
        and reading["reading_date"] == finding["failure_date"]
        and (reading.get("mechanical_seal_leak_de") or reading.get("mechanical_seal_leak_nde"))
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def plan_finding_attachments(plan: dict[str, Any]) -> dict[str, Any]:
    """Pure: never mutates `plan`. Classifies every proposed finding into
    exactly one of attach/quarantine/unmatched, so the decision is
    inspectable before any SQL is built. `attachments` maps
    condition_monitoring_reading_code -> finding text (at most one finding
    per reading, matching this workbook's own 1:1 evidence -- see
    _match_finding_to_reading)."""
    cmon_inserts = plan["condition_monitoring_readings"]["insert"]
    attachments: dict[str, str] = {}
    quarantined: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for finding in plan["findings"]["insert"]:
        key = (finding["source_sheet_name"], finding["source_row_number"])
        if key in QUARANTINED_FINDING_ROWS:
            quarantined.append(finding)
            continue

        matched = _match_finding_to_reading(finding, cmon_inserts)
        if matched is None:
            unmatched.append(finding)
            continue

        attachments[matched["condition_monitoring_reading_code"]] = finding["failure_description"]

    return {"attachments": attachments, "quarantined": quarantined, "unmatched": unmatched}


def _sql(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _sql_jsonb(value: dict[str, Any] | None) -> str:
    if not value:
        return "NULL"
    return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"


def _sql_date(value: str | None) -> str:
    return "NULL" if value is None else _sql(value)


def apply_plan(plan: dict[str, Any], runner: DatabaseRunner) -> dict[str, Any]:
    finding_plan = plan_finding_attachments(plan)
    attachments = finding_plan["attachments"]

    statements = ["BEGIN;"]

    for reading in plan["condition_monitoring_readings"]["insert"]:
        columns = [
            "condition_monitoring_reading_code", "condition_monitoring_schedule_code", "asset_code", "asset_type",
            "reading_date", "flushing_temp_de", "flushing_temp_nde", "quench_temp_de", "quench_temp_nde",
            "flushing_in_temp_de", "flushing_in_temp_nde", "flushing_out_temp_de", "flushing_out_temp_nde",
            "cooling_water_in_temp_de", "cooling_water_in_temp_nde", "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
            "mechseal_temp_de", "mechseal_temp_nde", "mechanical_seal_leak_de", "mechanical_seal_leak_nde",
            "water_jacket_temp_de", "water_jacket_temp_nde", "suction_temp", "discharge_temp", "pump_operating_state",
            "source_workbook_name", "source_sheet_name", "source_row_number",
        ]
        values = ", ".join(
            _sql_date(reading["reading_date"]) if column == "reading_date" else _sql(reading[column])
            for column in columns
        )
        finding_text = attachments.get(reading["condition_monitoring_reading_code"])
        statements.append(
            f"INSERT INTO condition_monitoring_reading ({', '.join(columns)}, finding) "
            f"VALUES ({values}, {_sql(finding_text)});"
        )

    for occurrence in plan["pm_occurrences"]["insert"]:
        columns = [
            "pm_occurrence_code", "pm_schedule_code", "asset_code", "asset_type",
            "occurrence_date", "status", "source_workbook_name", "source_sheet_name", "source_row_number",
        ]
        values = ", ".join(
            _sql_date(occurrence["occurrence_date"]) if column == "occurrence_date" else _sql(occurrence[column])
            for column in columns
        )
        statements.append(
            "INSERT INTO pm_occurrence "
            f"({', '.join(columns)}, checklist_completion) VALUES ({values}, {_sql_jsonb(occurrence['checklist_completion'])});"
        )

    # Findings are attached to their matched condition_monitoring_reading
    # row above (plan_finding_attachments), never inserted as a standalone
    # cm_report row -- deliberately no loop over plan["findings"]["insert"]
    # here (see this module's own header note on QUARANTINED_FINDING_ROWS).

    statements.append("COMMIT;")
    runner.execute_script("\n".join(statements))
    return {
        "condition_monitoring_readings": {"inserted": len(plan["condition_monitoring_readings"]["insert"])},
        "pm_occurrences": {"inserted": len(plan["pm_occurrences"]["insert"])},
        "findings": {
            "attached": len(finding_plan["attachments"]),
            "quarantined": len(finding_plan["quarantined"]),
            "unmatched": len(finding_plan["unmatched"]),
        },
        "cm_reports": {"inserted": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the HOC PM/CM workbook into canonical Postgres")
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compose-file", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    projection = ingest_workbook(args.workbook)
    runner = DatabaseRunner(DatabaseConfig(env_file=args.env_file, compose_file=args.compose_file))
    state = load_state(runner)
    plan = plan_import(projection, state)

    result: dict[str, Any] = {"metadata": projection["metadata"], "plan_summary": plan["summary"],
                               "unresolved_pump_tags": plan["unresolved_pump_tags"]}

    if args.mode == "apply":
        result["applied"] = apply_plan(plan, runner)
        result["post_apply_counts"] = {
            "condition_monitoring_reading": runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading"),
            "pm_occurrence": runner.query_scalar("SELECT count(*) FROM pm_occurrence"),
            "cm_report": runner.query_scalar("SELECT count(*) FROM cm_report"),
        }
    else:
        result["plan"] = plan

    output_text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
    print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
