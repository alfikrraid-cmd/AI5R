"""
MWO-LTSA-102C -- Import CLI tests (real execution).

Real Postgres throughout (the same docker-compose-exec-psql runtime this
whole session's ingestion/execution-engine/worker work has already used
and proven) -- no mock database. All test data is "TEST-CLI-" namespaced
and deleted in an autouse before/after fixture, so this suite leaves the
shared runtime database exactly as it found it.

MWO-LTSA-102's own "EXECUTION BLOCKED" stub is gone (closed by
MWO-LTSA-102B's build_canonical_packages() + this MWO's wiring) -- every
test below proves the real pipeline (adapt -> validate -> conflict-check ->
build_canonical_packages -> build_import_session -> ImportQueueManager ->
ImportWorker -> execute_import) actually reaches the database, not just
that it stops honestly before it.
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

_INGESTION_PATH = CORE_SERVICES_PATH.parents[0] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

import pytest  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from API.import_cli import (  # noqa: E402
    _EXIT_EXECUTION_FAILED,
    _EXIT_OK,
    _EXIT_UNSUPPORTED_INPUT,
    _EXIT_VALIDATION_FAILED,
    dry_run_import,
    main,
    run,
)
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query  # noqa: E402

_REPO_ROOT = CORE_SERVICES_PATH.parents[0]
_RUNTIME_DIR = _REPO_ROOT / "CORE-SERVICES" / "RUNTIME"
_ENV_FILE = _RUNTIME_DIR / ".env.verify.local"
_COMPOSE_FILE = _RUNTIME_DIR / "compose.yaml"


def _runner() -> DatabaseRunner:
    return DatabaseRunner(DatabaseConfig(env_file=_ENV_FILE, compose_file=_COMPOSE_FILE))


@pytest.fixture(scope="module")
def runner():
    return _runner()


@pytest.fixture(autouse=True)
def _cleanup(runner):
    _delete_test_rows(runner)
    yield
    _delete_test_rows(runner)


def _delete_test_rows(runner: DatabaseRunner) -> None:
    runner.execute_script(
        """
        DELETE FROM seal_engineering_document WHERE document_code LIKE 'TEST-CLI-%';
        DELETE FROM seal_registry WHERE seal_code LIKE 'TEST-CLI-%';
        DELETE FROM ltsa_pumps WHERE tag_number LIKE 'TEST-CLI-%';
        """
    )


def _write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _pump_present(runner: DatabaseRunner, tag_number: str) -> bool:
    rows = _json_query(f"SELECT tag_number FROM ltsa_pumps WHERE tag_number = '{tag_number}'", runner)
    return rows != []


# --- real execution: adapt -> ... -> execute_import -> real database write ---


def test_json_file_with_one_pump_is_executed_and_written_to_the_database(tmp_path, runner, capsys):
    path = _write_json(tmp_path, "package.json", {"pumps": [{"tag_number": "TEST-CLI-P-1", "area": "Unit 1"}]})

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "1 pumps" in output
    assert "valid=True" in output
    assert "Execution: status=COMMITTED" in output
    assert "final status=IMPORTED" in output
    assert "pump: inserted=1" in output
    assert _pump_present(runner, "TEST-CLI-P-1")


def test_multi_entity_package_produces_multiple_canonical_packages_and_writes_all_of_them(tmp_path, runner, capsys):
    path = _write_json(
        tmp_path,
        "multi.json",
        {
            "pumps": [{"tag_number": "TEST-CLI-P-MULTI-1", "area": "Unit 1"}],
            "seals": [{"seal_code": "TEST-CLI-S-MULTI-1", "seal_name": "Cartridge Seal"}],
            "installations": [],
            "documents": [],
        },
    )

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "2 CanonicalKnowledgePackage(s)" in output
    assert "pump: inserted=1" in output
    assert "seal: inserted=1" in output
    assert _pump_present(runner, "TEST-CLI-P-MULTI-1")
    live_seal = _json_query("SELECT seal_code FROM seal_registry WHERE seal_code = 'TEST-CLI-S-MULTI-1'", runner)
    assert live_seal != []


def test_empty_package_reports_ok_nothing_to_execute(tmp_path, runner, capsys):
    path = _write_json(tmp_path, "empty.json", {"pumps": [], "seals": [], "installations": [], "documents": []})

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "Nothing to execute" in output


def test_invalid_package_blocks_before_execution_with_validation_exit_code(tmp_path, runner, capsys):
    # tag_number present, `area` (required) missing.
    path = _write_json(tmp_path, "invalid.json", {"pumps": [{"tag_number": "TEST-CLI-P-BAD"}]})

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_VALIDATION_FAILED
    assert "MISSING_REQUIRED_FIELD" in output
    assert "BLOCKED" in output
    assert "validation error" in output
    # Never reached build_canonical_packages/execute_import at all.
    assert "Execution:" not in output
    assert not _pump_present(runner, "TEST-CLI-P-BAD")


def test_unsupported_extension_returns_a_distinct_exit_code(tmp_path, runner, capsys):
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_UNSUPPORTED_INPUT
    assert "UNSUPPORTED INPUT" in output


def test_folder_processes_and_executes_every_discovered_file(tmp_path, runner, capsys):
    folder = tmp_path / "batch"
    folder.mkdir()
    _write_json(folder, "a.json", {"pumps": [{"tag_number": "TEST-CLI-P-2", "area": "Unit 1"}]})
    _write_json(folder, "b.json", {"pumps": [{"tag_number": "TEST-CLI-P-3", "area": "Unit 2"}]})

    exit_code = run(folder, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert output.count("Execution: status=COMMITTED") == 2
    assert _pump_present(runner, "TEST-CLI-P-2")
    assert _pump_present(runner, "TEST-CLI-P-3")


# --- real conflict detection against the live database (not a mocked snapshot) ---


def test_an_unresolved_manual_review_conflict_makes_execute_import_itself_reject_the_write(tmp_path, runner, capsys):
    # Both sides have a real, DIFFERENT value for `area` -> RESOLUTION_
    # MANUAL_REVIEW, SEVERITY_HIGH, status OPEN (conflict_resolution.py) --
    # execute_import()'s own "reject if unresolved HIGH conflicts" rule
    # (import_execution_engine.py) then refuses the write for real. This is
    # no longer the CLI's own placeholder block -- it is the real execution
    # engine's real safety rule, exercised end to end.
    runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('TEST-CLI-P-EXISTING', 'Unit 1');")
    path = _write_json(
        tmp_path, "update.json", {"pumps": [{"tag_number": "TEST-CLI-P-EXISTING", "area": "Unit 2"}]}
    )

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_EXECUTION_FAILED
    assert "MANUAL_REVIEW" in output
    assert "Conflicts: 1" in output
    assert "Execution: status=REJECTED_CONFLICTS" in output
    # Never overwritten -- execute_import rejected before writing anything.
    live = _json_query("SELECT area FROM ltsa_pumps WHERE tag_number = 'TEST-CLI-P-EXISTING'", runner)
    assert live == [{"area": "Unit 1"}]


def test_a_real_create_new_conflict_is_inserted_successfully(tmp_path, runner, capsys):
    path = _write_json(
        tmp_path, "create-new.json", {"pumps": [{"tag_number": "TEST-CLI-P-NEW", "area": "Unit 1"}]}
    )

    exit_code = run(path, runner)
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "CREATE_NEW" in output
    assert "Execution: status=COMMITTED" in output
    assert _pump_present(runner, "TEST-CLI-P-NEW")


# --- main() argv wiring ------------------------------------------------------------


def test_main_wires_argv_path_and_database_args_through_to_run(tmp_path, capsys):
    path = _write_json(tmp_path, "via-main.json", {"pumps": [{"tag_number": "TEST-CLI-P-MAIN", "area": "Unit 1"}]})

    exit_code = main([str(path), "--env-file", str(_ENV_FILE), "--compose-file", str(_COMPOSE_FILE)])
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "Execution: status=COMMITTED" in output

    cleanup_runner = _runner()
    assert _pump_present(cleanup_runner, "TEST-CLI-P-MAIN")


# --- dry-run (MWO-LTSA-DATA-IMPORT-UI-001A) ---------------------------------
#
# Real Postgres throughout, same "TEST-CLI-" namespaced convention as the
# rest of this file. Fixture headers/sheet name mirror the real RU II
# acceptance workbook (LTSA_RU_II_Master_Pump_Canonical.xlsx: sheet "Master
# Pump", columns "Tag Number"/"Area"/"Pump Type"/"API Plan"/"Notes" among
# others) -- verified directly against that real file during this mission's
# own manual acceptance run (244 rows, 5 rejected for missing 'area', 0 DB
# writes, "Master Pump" sheet recognized, mapped_columns exactly {'Tag
# Number': 'tag_number', 'Area': 'area', 'Pump Type': 'pump_type', 'API
# Plan': 'api_plan', 'Notes': 'notes'}) -- the fixture below is a small,
# portable, CI-safe stand-in with the same real shape, not a re-derived one.

_MASTER_PUMP_HEADERS = ("Pump ID", "Tag Number", "Area", "Pump Type", "API Plan", "Notes")


def _save_workbook(path: Path, sheets) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets:
        worksheet = workbook.create_sheet(name)
        for row in rows:
            worksheet.append(row)
    workbook.save(path)


def _master_pump_workbook(path: Path, rows: tuple[tuple, ...]) -> Path:
    _save_workbook(path, [("Master Pump", (_MASTER_PUMP_HEADERS, *rows))])
    return path


def test_dry_run_recognizes_the_real_master_pump_sheet_name_and_writes_nothing(tmp_path):
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-1A", "Unit 1", "OH", "11/61", None),),
    )
    runner = _runner()

    report = dry_run_import(path, runner)

    assert report.sheet == "Master Pump"
    assert report.source_count == 1
    assert report.normalized_count == 1
    assert report.new_count == 1
    assert report.approval_ready is True
    assert not _pump_present(runner, "TEST-CLI-P-1A")


def test_dry_run_column_mapping_is_exact_and_deterministic_no_synonyms_invented(tmp_path):
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-1A", "Unit 1", "OH", "11/61", "some note"),),
    )
    runner = _runner()

    report = dry_run_import(path, runner)

    assert report.mapped_columns == {
        "Tag Number": "tag_number",
        "Area": "area",
        "Pump Type": "pump_type",
        "API Plan": "api_plan",
        "Notes": "notes",
    }
    # "Pump ID" has no canonical ltsa_pumps column -- never guessed into one.
    assert report.unmapped_columns == ("Pump ID",)


def test_dry_run_preserves_ab_and_arbr_as_four_distinct_pumps_never_merged(tmp_path):
    # Real pattern from the RU II acceptance workbook's own Validation Queue
    # sheet: 211-P-13A / 211-P-13AR / 211-P-13B / 211-P-13BR coexist as four
    # separate physical pumps (that sheet's own Notes column says so
    # explicitly: "Distinct physical pump; do not merge with AR/BR.").
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (
            ("PUMP-1", "TEST-CLI-P-13A", "Unit 1", "BB", "32/62", None),
            ("PUMP-2", "TEST-CLI-P-13AR", "Unit 1", "BB", "32/62", None),
            ("PUMP-3", "TEST-CLI-P-13B", "Unit 1", "BB", "32/62", None),
            ("PUMP-4", "TEST-CLI-P-13BR", "Unit 1", "BB", "32/62", None),
        ),
    )
    runner = _runner()

    report = dry_run_import(path, runner)

    assert report.normalized_count == 4
    assert report.new_count == 4  # four distinct entities, never collapsed to fewer
    assert report.rejected_count == 0
    assert not _pump_present(runner, "TEST-CLI-P-13A")


def test_dry_run_rejects_a_missing_tag_number_instead_of_guessing(tmp_path):
    # Tag identity ambiguous (missing entirely) -> reject via the existing
    # MISSING_REQUIRED_FIELD rule (import_validator.py's _require, reused
    # unmodified), never silently dropped or guessed into an entity id.
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", None, "Unit 1", "OH", "11/61", None),),
    )
    runner = _runner()

    report = dry_run_import(path, runner)

    assert report.source_count == 1
    assert report.normalized_count == 1
    assert report.rejected_count == 1
    assert report.approval_ready is False
    assert any(issue["code"] == "MISSING_REQUIRED_FIELD" for issue in report.row_issues)


def test_dry_run_rejects_missing_area_without_guessing_a_value(tmp_path):
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-NOAREA", None, "OH", "11/61", None),),
    )
    runner = _runner()

    report = dry_run_import(path, runner)

    assert report.normalized_count == 1
    assert report.rejected_count == 1
    assert report.valid_count == 0
    assert report.approval_ready is False
    assert report.row_issues[0]["code"] == "MISSING_REQUIRED_FIELD"
    assert report.row_issues[0]["entity_id"] == "TEST-CLI-P-NOAREA"


def test_dry_run_detects_an_existing_pump_as_update_not_new(tmp_path):
    runner = _runner()
    runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('TEST-CLI-P-EXISTS', 'Unit 1');")
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-EXISTS", "Unit 1", "OH", "11/61", None),),
    )

    report = dry_run_import(path, runner)

    assert report.new_count == 0
    assert report.update_count == 1
    # Still zero writes -- the seeded row above is untouched, not "confirmed
    # updated" by this dry-run.
    live_area = _json_query("SELECT area FROM ltsa_pumps WHERE tag_number = 'TEST-CLI-P-EXISTS'", runner)
    assert live_area == [{"area": "Unit 1"}]


def test_dry_run_zero_db_writes_proven_by_row_count_before_and_after(tmp_path):
    runner = _runner()
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (
            ("PUMP-1", "TEST-CLI-P-ZW-1", "Unit 1", "OH", "11/61", None),
            ("PUMP-2", "TEST-CLI-P-ZW-2", "Unit 1", "BB", "32/62", None),
        ),
    )
    before = _json_query("SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number LIKE 'TEST-CLI-%'", runner)

    dry_run_import(path, runner)

    after = _json_query("SELECT count(*) AS n FROM ltsa_pumps WHERE tag_number LIKE 'TEST-CLI-%'", runner)
    assert before == after


def test_dry_run_is_idempotent_across_repeated_calls(tmp_path):
    runner = _runner()
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-IDEMP", "Unit 1", "OH", "11/61", None),),
    )

    first = dry_run_import(path, runner, session_id="TEST-CLI-FIXED-SESSION")
    second = dry_run_import(path, runner, session_id="TEST-CLI-FIXED-SESSION")

    assert asdict(first) == asdict(second)
    assert not _pump_present(runner, "TEST-CLI-P-IDEMP")


def test_dry_run_cli_flag_prints_report_and_never_writes(tmp_path, capsys):
    path = _master_pump_workbook(
        tmp_path / "master.xlsx",
        (("PUMP-1", "TEST-CLI-P-CLI", "Unit 1", "OH", "11/61", None),),
    )

    exit_code = main([str(path), "--dry-run", "--env-file", str(_ENV_FILE), "--compose-file", str(_COMPOSE_FILE)])
    output = capsys.readouterr().out

    assert exit_code == _EXIT_OK
    assert "DRY RUN ONLY -- zero rows were inserted or updated." in output
    assert "session_id=" in output
    assert "new=1 update=0" in output
    assert not _pump_present(_runner(), "TEST-CLI-P-CLI")


def test_dry_run_on_a_folder_reports_unsupported_input_not_a_crash(tmp_path):
    folder = tmp_path / "batch"
    folder.mkdir()
    _master_pump_workbook(folder / "master.xlsx", (("PUMP-1", "TEST-CLI-P-FOLDER", "Unit 1", "OH", "11/61", None),))
    runner = _runner()

    exit_code = run(folder, runner, dry_run=True)

    assert exit_code == _EXIT_UNSUPPORTED_INPUT
