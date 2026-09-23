from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from hcc_june_cm_importer import parse_leak, parse_workbook, plan_import


WORKBOOK = Path(__file__).parents[4] / "TEMP" / "CM & PM Summary HCC JUNI.xlsx"


def test_hcc_june_dry_run_population_and_quarantine():
    rows, stats = parse_workbook(WORKBOOK)
    assets = {row["asset_code"]: "PUMP" for row in rows}
    assets["701-MM-51"] = None
    assets["702-MM-51"] = None
    plan = plan_import(rows, assets, set())

    assert stats == {"raw_rows": 385, "eligible": 182, "excluded": 203}
    assert len(plan["safe_insert"]) == 178
    assert len(plan["quarantined"]) == 4
    assert not plan["skip_existing"]
    assert not plan["block_ambiguous"]


def test_hcc_june_control_rows_preserve_fields_and_nulls():
    rows, _ = parse_workbook(WORKBOOK)
    controls = {(row["asset_code"], row["reading_date"]): row for row in rows if row["asset_code"] == "701-P-1A"}

    old = controls["701-P-1A", "2026-06-12"]
    assert old["api_plan_snapshot"] == "23/61"
    assert old["flushing_temp_de"] == 30
    assert old["flushing_in_temp_de"] == 34
    assert old["mechanical_seal_leak_de"] is True
    assert old["flushing_temp_nde"] is None
    assert old["pump_operating_state"] == "Standby"

    new = controls["701-P-1A", "2026-06-26"]
    assert new["flushing_temp_de"] == 52
    assert new["flushing_in_temp_de"] == 65
    assert new["mechanical_seal_leak_de"] is False
    assert new["suction_temp"] == 247
    assert new["pump_operating_state"] == "Running"


def test_leak_blank_is_null_and_existing_collision_is_skipped():
    assert parse_leak("") is None
    rows, _ = parse_workbook(WORKBOOK)
    first = rows[0]
    plan = plan_import([first], {first["asset_code"]: "PUMP"}, {(first["asset_code"], first["reading_date"])})
    assert len(plan["skip_existing"]) == 1
    assert not plan["safe_insert"]
