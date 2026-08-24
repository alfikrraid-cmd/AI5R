from __future__ import annotations

import sys
from pathlib import Path

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKBOOK_PATH = REPO_ROOT / "CM & PM Summary HOC JUNI.xlsx"

from ltsa_hoc_pm_cm_db_upsert import (  # noqa: E402
    QUARANTINED_FINDING_ROWS,
    _match_finding_to_reading,
    apply_plan,
    plan_finding_attachments,
)
from ltsa_hoc_pm_cm_ingestion import ingest_workbook  # noqa: E402
from ltsa_hoc_pm_cm_upsert import plan_import  # noqa: E402

_TEMPERATURE_FIELDS = [
    "flushing_temp_de", "flushing_temp_nde", "quench_temp_de", "quench_temp_nde",
    "flushing_in_temp_de", "flushing_in_temp_nde", "flushing_out_temp_de", "flushing_out_temp_nde",
    "cooling_water_in_temp_de", "cooling_water_in_temp_nde", "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
    "mechseal_temp_de", "mechseal_temp_nde", "water_jacket_temp_de", "water_jacket_temp_nde",
    "suction_temp", "discharge_temp",
]


class FakeRunner:
    """Records every executed script; never touches a real database. Used
    to test apply_plan()'s generated SQL shape without any DB write."""

    def __init__(self):
        self.scripts: list[str] = []

    def execute_script(self, sql: str) -> None:
        self.scripts.append(sql)


def _reading(asset_code="140-P-3A", reading_date="2026-06-15", leak_de=None, leak_nde=None, code="LTSA-CMONR-TEST"):
    return {
        "condition_monitoring_reading_code": code,
        "asset_code": asset_code,
        "reading_date": reading_date,
        "mechanical_seal_leak_de": leak_de,
        "mechanical_seal_leak_nde": leak_nde,
    }


def _finding(tag_number="140-P-3A", failure_date="2026-06-15", sheet="finnding", row=1, text="leak text"):
    # Matches plan_import()'s own finalized findings["insert"] shape
    # (CORE-SERVICES/../ltsa_hoc_pm_cm_upsert.py) -- "asset_code", not the
    # raw projection's "tag_number".
    return {
        "source_sheet_name": sheet,
        "source_row_number": row,
        "asset_code": tag_number,
        "failure_date": failure_date,
        "failure_description": text,
    }


# 1. _match_finding_to_reading -- never guesses


def test_match_finding_to_reading_returns_the_unique_leak_match():
    finding = _finding()
    reading = _reading(leak_de=True, code="LTSA-CMONR-A")
    other = _reading(asset_code="200-P-1A", code="LTSA-CMONR-B")

    matched = _match_finding_to_reading(finding, [reading, other])

    assert matched is not None
    assert matched["condition_monitoring_reading_code"] == "LTSA-CMONR-A"


def test_match_finding_to_reading_returns_none_for_a_dateless_finding():
    finding = _finding(failure_date=None)
    reading = _reading(leak_de=True)

    assert _match_finding_to_reading(finding, [reading]) is None


def test_match_finding_to_reading_returns_none_when_no_leak_reading_matches():
    finding = _finding()
    reading = _reading(leak_de=None, leak_nde=None)  # same pump/date, but no leak flag

    assert _match_finding_to_reading(finding, [reading]) is None


def test_match_finding_to_reading_returns_none_for_an_ambiguous_same_day_double_leak():
    # 110-P-12B's real shape: two leak readings, same pump, no date on the
    # finding to disambiguate between them -- but even WITH a date, two
    # candidates on the exact same day must never be silently picked from.
    finding = _finding(tag_number="110-P-12B", failure_date="2026-06-18")
    reading_a = _reading(asset_code="110-P-12B", reading_date="2026-06-18", leak_de=True, code="LTSA-CMONR-A")
    reading_b = _reading(asset_code="110-P-12B", reading_date="2026-06-18", leak_nde=True, code="LTSA-CMONR-B")

    assert _match_finding_to_reading(finding, [reading_a, reading_b]) is None


# 2. plan_finding_attachments -- classification + quarantine


def _plan(findings, cmon_inserts):
    return {
        "condition_monitoring_readings": {"insert": cmon_inserts},
        "findings": {"insert": findings},
    }


def test_plan_finding_attachments_attaches_a_safely_matched_finding():
    finding = _finding(sheet="finnding", row=99, text="Mechseal Bocor dari drain gland")
    reading = _reading(leak_de=True, code="LTSA-CMONR-XYZ")

    result = plan_finding_attachments(_plan([finding], [reading]))

    assert result["attachments"] == {"LTSA-CMONR-XYZ": "Mechseal Bocor dari drain gland"}
    assert result["quarantined"] == []
    assert result["unmatched"] == []


def test_plan_finding_attachments_quarantines_140_p_13a_even_though_it_has_a_unique_match():
    finding = _finding(tag_number="140-P-13A", sheet="finnding", row=10)
    reading = _reading(asset_code="140-P-13A", leak_de=True, code="LTSA-CMONR-140P13A")

    result = plan_finding_attachments(_plan([finding], [reading]))

    assert result["attachments"] == {}
    assert len(result["quarantined"]) == 1
    assert result["quarantined"][0]["source_row_number"] == 10


def test_plan_finding_attachments_quarantines_110_p_12b_row_7():
    finding = _finding(tag_number="110-P-12B", failure_date=None, sheet="finnding", row=7)

    result = plan_finding_attachments(_plan([finding], []))

    assert result["attachments"] == {}
    assert len(result["quarantined"]) == 1
    assert result["unmatched"] == []


def test_plan_finding_attachments_reports_a_genuinely_unmatched_finding_separately_from_quarantine():
    # A finding that is neither in the explicit quarantine list nor
    # safely matchable must be reported as unmatched, not silently
    # dropped and not conflated with the named quarantine reasons.
    finding = _finding(sheet="finnding", row=42, failure_date="2026-06-01")

    result = plan_finding_attachments(_plan([finding], []))

    assert result["attachments"] == {}
    assert result["quarantined"] == []
    assert len(result["unmatched"]) == 1


def test_quarantined_finding_rows_names_exactly_the_two_approved_exclusions():
    assert QUARANTINED_FINDING_ROWS == frozenset({("finnding", 10), ("finnding", 7)})


# 3. apply_plan -- generated SQL shape, never touches a real DB


def test_apply_plan_never_creates_a_cm_report_row():
    finding = _finding(sheet="finnding", row=99)
    reading = _reading(leak_de=True, code="LTSA-CMONR-A")
    plan = {
        "condition_monitoring_readings": {"insert": [
            {**reading, "asset_type": "PUMP", "flushing_temp_de": 78, "flushing_temp_nde": None,
             "quench_temp_de": None, "quench_temp_nde": None, "flushing_in_temp_de": None, "flushing_in_temp_nde": None,
             "flushing_out_temp_de": None, "flushing_out_temp_nde": None, "cooling_water_in_temp_de": None,
             "cooling_water_in_temp_nde": None, "cooling_water_out_temp_de": None, "cooling_water_out_temp_nde": None,
             "mechseal_temp_de": None, "mechseal_temp_nde": None, "water_jacket_temp_de": None,
             "water_jacket_temp_nde": None, "suction_temp": None, "discharge_temp": None, "pump_operating_state": "Running",
             "condition_monitoring_schedule_code": "UNSCHEDULED::test.xlsx",
             "source_workbook_name": "test.xlsx", "source_sheet_name": "CM Measuring Report", "source_row_number": 10},
        ]},
        "pm_occurrences": {"insert": []},
        "findings": {"insert": [finding]},
    }
    runner = FakeRunner()

    result = apply_plan(plan, runner)

    sql = runner.scripts[0]
    assert "INSERT INTO cm_report" not in sql
    assert result["cm_reports"]["inserted"] == 0
    assert result["findings"]["attached"] == 1


def test_apply_plan_attaches_finding_text_onto_the_matched_condition_monitoring_reading_insert():
    finding = _finding(sheet="finnding", row=99, text="Mechseal Bocor dari drain gland durasi 1/3 detik")
    plan = {
        "condition_monitoring_readings": {"insert": [
            {"condition_monitoring_reading_code": "LTSA-CMONR-A", "condition_monitoring_schedule_code": "UNSCHEDULED::test.xlsx",
             "asset_code": "140-P-3A", "asset_type": "PUMP", "reading_date": "2026-06-15",
             "flushing_temp_de": 78, "flushing_temp_nde": None, "quench_temp_de": 100, "quench_temp_nde": None,
             "flushing_in_temp_de": None, "flushing_in_temp_nde": None, "flushing_out_temp_de": None, "flushing_out_temp_nde": None,
             "cooling_water_in_temp_de": None, "cooling_water_in_temp_nde": None, "cooling_water_out_temp_de": None,
             "cooling_water_out_temp_nde": None, "mechseal_temp_de": 123, "mechseal_temp_nde": None,
             "mechanical_seal_leak_de": True, "mechanical_seal_leak_nde": None,
             "water_jacket_temp_de": None, "water_jacket_temp_nde": None, "suction_temp": None, "discharge_temp": None,
             "pump_operating_state": "Running", "source_workbook_name": "test.xlsx",
             "source_sheet_name": "CM Measuring Report", "source_row_number": 10},
        ]},
        "pm_occurrences": {"insert": []},
        "findings": {"insert": [finding]},
    }
    runner = FakeRunner()

    apply_plan(plan, runner)

    sql = runner.scripts[0]
    assert "Mechseal Bocor dari drain gland durasi 1/3 detik" in sql
    # Verbatim temperature values preserved, never altered by attaching a finding.
    assert ", 78," in sql or "78," in sql
    assert "123" in sql


def test_apply_plan_never_attaches_a_quarantined_findings_text_anywhere():
    quarantined_finding = _finding(tag_number="140-P-13A", sheet="finnding", row=10, text="QUARANTINED TEXT MARKER")
    reading = {"condition_monitoring_reading_code": "LTSA-CMONR-A", "condition_monitoring_schedule_code": "UNSCHEDULED::test.xlsx",
               "asset_code": "140-P-13A", "asset_type": "PUMP", "reading_date": "2026-06-15",
               "flushing_temp_de": None, "flushing_temp_nde": None, "quench_temp_de": None, "quench_temp_nde": None,
               "flushing_in_temp_de": None, "flushing_in_temp_nde": None, "flushing_out_temp_de": None, "flushing_out_temp_nde": None,
               "cooling_water_in_temp_de": None, "cooling_water_in_temp_nde": None, "cooling_water_out_temp_de": None,
               "cooling_water_out_temp_nde": None, "mechseal_temp_de": None, "mechseal_temp_nde": None,
               "mechanical_seal_leak_de": True, "mechanical_seal_leak_nde": None,
               "water_jacket_temp_de": None, "water_jacket_temp_nde": None, "suction_temp": None, "discharge_temp": None,
               "pump_operating_state": "Running", "source_workbook_name": "test.xlsx",
               "source_sheet_name": "CM Measuring Report", "source_row_number": 10}
    plan = {
        "condition_monitoring_readings": {"insert": [reading]},
        "pm_occurrences": {"insert": []},
        "findings": {"insert": [quarantined_finding]},
    }
    runner = FakeRunner()

    result = apply_plan(plan, runner)

    sql = runner.scripts[0]
    assert "QUARANTINED TEXT MARKER" not in sql
    assert result["findings"]["quarantined"] == 1
    assert result["findings"]["attached"] == 0


def test_apply_plan_preserves_pm_occurrence_insert_shape_with_no_temperature_field():
    plan = {
        "condition_monitoring_readings": {"insert": []},
        "pm_occurrences": {"insert": [
            {"pm_occurrence_code": "LTSA-PMO-A", "pm_schedule_code": "UNSCHEDULED::test.xlsx",
             "asset_code": "140-P-21B", "asset_type": "PUMP", "occurrence_date": "2026-06-15",
             "status": "DONE", "checklist_completion": {"Flushing Line": True},
             "source_workbook_name": "test.xlsx", "source_sheet_name": " PM Mech Seal", "source_row_number": 11},
        ]},
        "findings": {"insert": []},
    }
    runner = FakeRunner()

    result = apply_plan(plan, runner)

    sql = runner.scripts[0]
    assert "INSERT INTO pm_occurrence" in sql
    assert '"Flushing Line": true' in sql or "Flushing Line" in sql
    # No temperature-shaped column name appears in the pm_occurrence statement.
    pm_occurrence_line = next(line for line in sql.splitlines() if line.startswith("INSERT INTO pm_occurrence"))
    assert "temp" not in pm_occurrence_line
    assert result["pm_occurrences"]["inserted"] == 1


# 4. End-to-end against the real workbook -- exact mission gate + idempotency.
# Skips gracefully if the workbook isn't present in this checkout rather
# than failing the whole suite on an environment difference.

import pytest  # noqa: E402

try:
    import openpyxl  # noqa: F401

    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False


@pytest.mark.skipif(not WORKBOOK_PATH.exists(), reason="real workbook not present in this checkout")
@pytest.mark.skipif(not _HAS_OPENPYXL, reason="openpyxl not installed")
def test_real_workbook_dry_run_matches_the_exact_mission_gate():
    projection = ingest_workbook(WORKBOOK_PATH)
    state = {
        "pumps": [
            {"tag_number": tag}
            for tag in {
                *(row["tag_number"] for row in projection["pm_occurrences"]),
                *(row["tag_number"] for row in projection["condition_monitoring_readings"]),
            }
        ],
        "condition_monitoring_readings": [],
        "pm_occurrences": [],
        "cm_reports": [],
    }

    plan = plan_import(projection, state)
    finding_plan = plan_finding_attachments(plan)

    assert len(plan["pm_occurrences"]["insert"]) == 19
    assert len(plan["condition_monitoring_readings"]["insert"]) == 114
    assert plan["unresolved_pump_tag_count"] == 0

    with_temperature = sum(
        1
        for reading in plan["condition_monitoring_readings"]["insert"]
        if any(reading[field] is not None for field in _TEMPERATURE_FIELDS)
    )
    assert with_temperature == 113

    assert len(finding_plan["attachments"]) == 7
    assert len(finding_plan["quarantined"]) == 2
    assert len(finding_plan["unmatched"]) == 0

    quarantined_rows = {(f["source_sheet_name"], f["source_row_number"]) for f in finding_plan["quarantined"]}
    assert quarantined_rows == {("finnding", 10), ("finnding", 7)}

    # Traceability: every proposed insert carries its exact source coordinate.
    for row in plan["pm_occurrences"]["insert"] + plan["condition_monitoring_readings"]["insert"]:
        assert row["source_workbook_name"] == "CM & PM Summary HOC JUNI.xlsx"
        assert row["source_sheet_name"]
        assert row["source_row_number"] is not None


@pytest.mark.skipif(not WORKBOOK_PATH.exists(), reason="real workbook not present in this checkout")
@pytest.mark.skipif(not _HAS_OPENPYXL, reason="openpyxl not installed")
def test_real_workbook_apply_then_reimport_is_idempotent_with_no_duplicate_ids():
    projection = ingest_workbook(WORKBOOK_PATH)
    pump_tags = {
        *(row["tag_number"] for row in projection["pm_occurrences"]),
        *(row["tag_number"] for row in projection["condition_monitoring_readings"]),
    }
    state = {
        "pumps": [{"tag_number": tag} for tag in pump_tags],
        "condition_monitoring_readings": [],
        "pm_occurrences": [],
        "cm_reports": [],
    }

    plan_run_1 = plan_import(projection, state)
    runner = FakeRunner()
    result_1 = apply_plan(plan_run_1, runner)

    assert result_1["condition_monitoring_readings"]["inserted"] == 114
    assert result_1["pm_occurrences"]["inserted"] == 19
    assert result_1["findings"]["attached"] == 7
    assert result_1["findings"]["quarantined"] == 2
    assert result_1["cm_reports"]["inserted"] == 0

    # Simulate the DB state after RUN_1 by feeding the newly-generated
    # codes back in as "already existing" -- exactly what load_state()
    # would report against a real database after a real apply.
    state_after_run_1 = {
        "pumps": state["pumps"],
        "condition_monitoring_readings": [
            {"condition_monitoring_reading_code": r["condition_monitoring_reading_code"]}
            for r in plan_run_1["condition_monitoring_readings"]["insert"]
        ],
        "pm_occurrences": [
            {"pm_occurrence_code": r["pm_occurrence_code"]}
            for r in plan_run_1["pm_occurrences"]["insert"]
        ],
        "cm_reports": [],
    }

    plan_run_2 = plan_import(projection, state_after_run_1)

    assert len(plan_run_2["condition_monitoring_readings"]["insert"]) == 0
    assert len(plan_run_2["pm_occurrences"]["insert"]) == 0
    assert len(plan_run_2["condition_monitoring_readings"]["unchanged"]) == 114
    assert len(plan_run_2["pm_occurrences"]["unchanged"]) == 19

    # No duplicate IDs: every RUN_1 code is deterministic and reappears
    # identically as "unchanged" in RUN_2 -- never a second, different code
    # for the same source row.
    run_1_cmon_codes = {r["condition_monitoring_reading_code"] for r in plan_run_1["condition_monitoring_readings"]["insert"]}
    assert run_1_cmon_codes == set(plan_run_2["condition_monitoring_readings"]["unchanged"])
    run_1_pmo_codes = {r["pm_occurrence_code"] for r in plan_run_1["pm_occurrences"]["insert"]}
    assert run_1_pmo_codes == set(plan_run_2["pm_occurrences"]["unchanged"])
