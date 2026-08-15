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
        statements.append(
            f"INSERT INTO condition_monitoring_reading ({', '.join(columns)}) VALUES ({values});"
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

    for finding in plan["findings"]["insert"]:
        columns = [
            "cm_report_code", "asset_code", "asset_type", "failure_category", "severity",
            "failure_description", "status", "source_workbook_name", "source_sheet_name", "source_row_number",
        ]
        values = ", ".join(_sql(finding[column]) for column in columns)
        statements.append(
            "INSERT INTO cm_report "
            f"({', '.join(columns)}, failure_date) VALUES ({values}, {_sql_date(finding['failure_date'])});"
        )

    statements.append("COMMIT;")
    runner.execute_script("\n".join(statements))
    return {
        entity: {"inserted": len(plan[entity]["insert"])}
        for entity in ("condition_monitoring_readings", "pm_occurrences", "findings")
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
