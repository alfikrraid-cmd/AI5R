"""LTSA_HISTORICAL_INSTALLATION_2024_2025_IMPORT_IMPLEMENTATION_R1 -- disposable
Postgres (docker run postgres:16-alpine, removed afterwards) end-to-end tests:
migration 039 on top of the canonical schema + 018 + 036, the governed
executor's dry-run / apply / idempotent re-run, DB-level append-only
protection, atomic rollback, and the read models (lifecycle timeline, MTBF,
Current Installation isolation).

The full frozen-manifest replay (88 approved rows + the 42 governed
installation reports) is DATA-GATED: it runs only when both external,
uncommitted inputs are provided --
  LTSA_HIST_INSTALL_MANIFEST  path to the approved manifest (sha256 6bae2f11...)
  LTSA_HIST_INSTALL_BASELINE  path to a read-only production snapshot JSON
                              (asset_registry, ltsa_pumps, installation_report)
Skipped (never faked) when docker or those files are unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

_INGESTION_PATH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _INGESTION_PATH.parents[2]
for extra in (_INGESTION_PATH, _REPO_ROOT / "CORE-SERVICES"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import historical_installation_manifest_executor as ex  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query, _sql, bootstrap_schema  # noqa: E402

_DB_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_MIGRATIONS = [_DB_DIR / "MIGRATIONS" / name for name in (
    "018_create_seal_unit.sql",
    "036_create_historical_seal_service_activity.sql",
    "039_extend_historical_seal_service_activity_governed_evidence.sql",
)]
_CONTAINER = "ai5r-test-historical-installation-import-pg"
_USER, _PASSWORD, _DATABASE = "ai5r", "test-historical-installation-password", "ltsa_brain"
NOW = datetime(2026, 9, 27, 5, 0, tzinfo=timezone.utc)

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI unavailable")


@pytest.fixture(scope="module")
def pg_port():
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        pytest.skip("docker daemon unavailable")
    subprocess.run(["docker", "rm", "-f", _CONTAINER], capture_output=True, text=True)
    subprocess.run(["docker", "run", "-d", "--name", _CONTAINER, "-e", f"POSTGRES_USER={_USER}",
                    "-e", f"POSTGRES_PASSWORD={_PASSWORD}", "-e", f"POSTGRES_DB={_DATABASE}",
                    "-p", "127.0.0.1::5432", "postgres:16-alpine"], check=True, capture_output=True, text=True)
    try:
        port = int(subprocess.run(["docker", "port", _CONTAINER, "5432/tcp"], check=True, capture_output=True,
                                  text=True).stdout.strip().splitlines()[0].rsplit(":", 1)[1])
        probe = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=port, user=_USER, password=_PASSWORD, database=_DATABASE))
        for _ in range(60):
            try:
                probe.query_scalar("SELECT 1")
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        else:
            raise RuntimeError("disposable Postgres never became ready")
        yield port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER], capture_output=True, text=True)


def fresh_db(port) -> DatabaseRunner:
    runner = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=port, user=_USER, password=_PASSWORD, database=_DATABASE))
    runner.execute_script("DROP SCHEMA public CASCADE; CREATE SCHEMA public; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    bootstrap_schema(runner, _DB_DIR / "CANONICAL_SCHEMA.sql")
    for migration in _MIGRATIONS:
        bootstrap_schema(runner, migration)
    return runner


def seed(runner, registry, ltsa_pumps, installations):
    area = {r["asset_code"]: r.get("area") for r in registry}
    statements = []
    for r in registry:
        statements.append(f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) VALUES "
                          f"({_sql(r['asset_code'])}, {_sql(r['asset_code'])}, {_sql(r.get('asset_type'))}, {_sql(r.get('area'))});")
    for tag in ltsa_pumps:
        statements.append(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ({_sql(tag)}, {_sql(area.get(tag) or 'UNKNOWN')});")
    for i in installations:
        statements.append("INSERT INTO installation_report (installation_code, report_no, report_date, plant_equip_no, "
                          "pump_tag_number, seal_type, seal_size, seal_location, source_document_name) VALUES ("
                          + ", ".join(_sql(i.get(k)) for k in ("installation_code", "report_no", "report_date", "plant_equip_no",
                                                               "pump_tag_number", "seal_type", "seal_size", "seal_location",
                                                               "source_document_name")) + ");")
    runner.execute_script("\n".join(statements))


def executor_args(path, sha, rows, port, *, apply=False, expected_inserts=None, confirm=None):
    return argparse.Namespace(manifest=path, expected_sha256=sha, expected_rows=rows, apply=apply,
                              expected_inserts=expected_inserts, confirm_historical_installation_import=confirm,
                              env_file=None, compose_file=None, service="postgres", db_user=_USER, database=_DATABASE,
                              host="127.0.0.1", port=port, password=_PASSWORD, report=None)


def count(runner, sql):
    return int(runner.query_scalar(sql).strip().splitlines()[-1])


def expect_rejected(runner, sql):
    with pytest.raises(Exception) as err:
        runner.execute_script(sql)
    assert "append-only" in str(err.value)


def timeline_service(runner):
    from API.equipment_timeline_service import EquipmentTimelineService
    from API.historical_seal_service_activity_repository import HistoricalSealServiceActivityRepository
    from API.installation_report_repository import InstallationReportRepository
    from API.TESTS.test_current_installation import FakeGateway, FakeKnowledgeService, knowledge_for

    def build(tag):
        return EquipmentTimelineService(
            knowledge_service=FakeKnowledgeService(knowledge_for(tag)),
            installation_gateway=FakeGateway("list_installations", []),
            work_order_gateway=FakeGateway("list_work_orders", []),
            maintenance_history_gateway=FakeGateway("list_maintenance_history", []),
            pm_occurrence_gateway=FakeGateway("list_pm_occurrences", []),
            seal_gateway=FakeGateway("list_seals", []),
            installation_report_repository=InstallationReportRepository(runner),
            historical_seal_service_activity_repository=HistoricalSealServiceActivityRepository(runner),
        )
    return build


# -- synthetic end-to-end (always, when docker is available) -------------------------------------


def _synthetic(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_historical_installation_manifest_executor import base_rows, manifest_bytes
    data = manifest_bytes(base_rows())
    path = tmp_path / "approved.json"
    path.write_bytes(data)
    return path, ex.sha256_bytes(data)


def _seed_synthetic(runner):
    registry = [{"asset_code": t, "asset_type": "PUMP", "area": "HCC"} for t in ("701-P-2", "200-P-7A", "220-P-1B")]
    seed(runner, registry, [r["asset_code"] for r in registry], [
        {"installation_code": "INSTL-011-2026", "report_no": "011/INSTL/TAP/02-2026", "report_date": "2026-02-23", "plant_equip_no": "701-P-2",
         "pump_tag_number": "701-P-2", "seal_type": "T48MP", "seal_size": '1.7/8"',
         "source_document_name": "SCAN 011 INSTALLATION REPORT 701-P-2.pdf"}])


def test_migration_is_additive_and_idempotent(pg_port):
    runner = fresh_db(pg_port)
    bootstrap_schema(runner, _MIGRATIONS[-1])  # re-apply 039: no error, no change
    columns = {r["column_name"] for r in _json_query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'historical_seal_service_activity'", runner)}
    for col in ("source_reference", "raw_tag", "event_date", "date_status", "historical_event_id", "source_fingerprint",
                "event_fingerprint", "position", "position_source_raw", "source_date_raw", "parsed_source_date",
                "corrected_event_date", "date_correction_status", "date_correction_reason", "evidence_grade",
                "deduplication_status", "import_manifest_sha256", "imported_at"):
        assert col in columns
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 0


def test_executor_lifecycle_append_only_and_read_models(pg_port, tmp_path):
    runner = fresh_db(pg_port)
    _seed_synthetic(runner)
    path, sha = _synthetic(tmp_path)

    dry = ex.run(executor_args(path, sha, 3, pg_port), approved_manifest_sha256=sha)
    assert (dry["PREFLIGHT"]["PROPOSED_INSERT"], dry["PREFLIGHT"]["ALREADY_IMPORTED"]) == (3, 0)
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 0

    applied = ex.run(executor_args(path, sha, 3, pg_port, apply=True, expected_inserts=3, confirm=sha),
                     approved_manifest_sha256=sha)
    assert applied["APPLY"]["INSERTED"] == 3 and applied["VERIFY"]["FIELD_IDENTICAL"] is True

    again = ex.run(executor_args(path, sha, 3, pg_port), approved_manifest_sha256=sha)
    assert (again["PREFLIGHT"]["PROPOSED_INSERT"], again["PREFLIGHT"]["ALREADY_IMPORTED"]) == (0, 3)
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 3

    stored = _json_query("SELECT raw_tag, event_date::text AS event_date, parsed_source_date::text AS parsed_source_date, "
                         "corrected_event_date::text AS corrected, date_correction_status, seal_size, position "
                         "FROM historical_seal_service_activity ORDER BY raw_tag", runner)
    by_tag = {r["raw_tag"]: r for r in stored}
    assert (by_tag["701-P-2"]["event_date"], by_tag["701-P-2"]["parsed_source_date"], by_tag["701-P-2"]["corrected"]) == \
        ("2024-01-11", "2024-11-01", "2024-01-11")
    assert by_tag["701-P-2"]["seal_size"] == "1.7/8''" and by_tag["200-P-7A"]["position"] == "DE"

    expect_rejected(runner, "UPDATE historical_seal_service_activity SET remarks = 'x'")
    expect_rejected(runner, "DELETE FROM historical_seal_service_activity")
    expect_rejected(runner, "TRUNCATE historical_seal_service_activity")
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 3

    build = timeline_service(runner)
    svc = build("701-P-2")
    lifecycle = svc.build_lifecycle("701-P-2")
    titles = [e.title for e in lifecycle.timeline if e.source.value == "SERVICE_ACTIVITY"]
    assert titles == ["Historical Service Activity (T48MP)"]
    mtbf = svc.build_installation_based_mtbf("701-P-2")
    assert [(i.previous_installation_date, i.next_installation_date, i.mtbf_days) for i in mtbf.intervals] == \
        [("2024-01-11", "2026-02-23", 774)]
    current = svc.build_current_installation("701-P-2", now=NOW).current
    assert (current.source_installation_code, current.installation_date) == ("INSTL-011-2026", "2026-02-23")
    refurb = [e.title for e in build("220-P-1B").build_lifecycle("220-P-1B").timeline if e.source.value == "SERVICE_ACTIVITY"]
    assert refurb == ["Reinstallation (Refurbished Seal) (T8B1)"]
    assert build("220-P-1B").build_current_installation("220-P-1B", now=NOW).current.installation_status == "NOT_RECORDED"


def test_in_database_precheck_rolls_back_the_whole_batch(pg_port, tmp_path):
    runner = fresh_db(pg_port)
    _seed_synthetic(runner)
    path, sha = _synthetic(tmp_path)
    manifest = ex.parse_manifest(path.read_bytes(), sha, expected_rows=3)
    rows = list(manifest.rows)
    # A governed installation_report appears on a batch pump/date after preflight: the
    # in-transaction precheck must abort the whole batch.
    runner.execute_script("INSERT INTO installation_report (installation_code, report_no, report_date, pump_tag_number, "
                          "source_document_name) VALUES ('INSTL-RACE', 'RACE', '2024-05-07', '200-P-7A', 'race.pdf');")
    store = ex.PostgresHistoricalInstallationStore(runner)
    with pytest.raises(Exception) as err:
        store.insert_all(rows, sha, 0)
    assert "GOVERNED_INSTALLATION_CONFLICT" in str(err.value)
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 0


def test_database_rejects_an_unapproved_correction_even_outside_the_executor(pg_port):
    runner = fresh_db(pg_port)
    _seed_synthetic(runner)
    with pytest.raises(Exception):
        runner.execute_script(
            "INSERT INTO historical_seal_service_activity (source_reference, source_year, source_filename, source_worksheet, "
            "source_row, raw_tag, tag_match_outcome, date_status, event_date, date_correction_status, corrected_event_date) "
            "VALUES ('X', 2024, 'f', 's', 1, '701-P-2', 'EXACT', 'VALID', '2024-01-11', 'APPROVED', '2024-02-11');")
    with pytest.raises(Exception):
        runner.execute_script(
            "INSERT INTO historical_seal_service_activity (source_reference, source_year, source_filename, source_worksheet, "
            "source_row, raw_tag, tag_match_outcome, date_status, position) VALUES ('Y', 2024, 'f', 's', 1, 'x', 'EXACT', 'VALID', 'BOTH');")


# -- DATA-GATED: frozen approved manifest + production baseline ---------------------------------------------


_MANIFEST = os.environ.get("LTSA_HIST_INSTALL_MANIFEST")
_BASELINE = os.environ.get("LTSA_HIST_INSTALL_BASELINE")


@pytest.mark.skipif(not (_MANIFEST and _BASELINE and Path(_MANIFEST).is_file() and Path(_BASELINE).is_file()),
                    reason="frozen manifest / production baseline snapshot not provided (never committed)")
def test_frozen_manifest_full_replay(pg_port):
    from API.current_installation_contract import STATUS_INSTALLED
    manifest_path = Path(_MANIFEST)
    assert ex.sha256_bytes(manifest_path.read_bytes()) == ex.APPROVED_MANIFEST_SHA256
    baseline = json.loads(Path(_BASELINE).read_text(encoding="utf-8"))
    runner = fresh_db(pg_port)
    seed(runner, baseline["asset_registry"], baseline["ltsa_pumps"], baseline["installation_report"])
    assert count(runner, "SELECT count(*) FROM historical_seal_service_activity") == 0

    first = ex.run(executor_args(manifest_path, ex.APPROVED_MANIFEST_SHA256, ex.APPROVED_MANIFEST_ROWS, pg_port))
    assert (first["PREFLIGHT"]["PROPOSED_INSERT"], first["PREFLIGHT"]["ALREADY_IMPORTED"]) == (88, 0)
    applied = ex.run(executor_args(manifest_path, ex.APPROVED_MANIFEST_SHA256, 88, pg_port, apply=True,
                                   expected_inserts=88, confirm=ex.APPROVED_MANIFEST_SHA256))
    assert applied["APPLY"]["INSERTED"] == 88 and applied["VERIFY"]["FIELD_IDENTICAL"] is True
    second = ex.run(executor_args(manifest_path, ex.APPROVED_MANIFEST_SHA256, 88, pg_port))
    assert (second["PREFLIGHT"]["PROPOSED_INSERT"], second["PREFLIGHT"]["ALREADY_IMPORTED"]) == (0, 88)

    stats = _json_query(
        "SELECT source_year, count(*) AS n, count(*) FILTER (WHERE date_correction_status = 'APPROVED') AS corrections, "
        "count(*) FILTER (WHERE position <> 'PUMP_LEVEL') AS positioned, "
        "count(*) FILTER (WHERE event_type = 'REINSTALLATION_REFURBISHED_SEAL') AS reinstall "
        "FROM historical_seal_service_activity GROUP BY source_year ORDER BY source_year", runner)
    assert [(s["source_year"], s["n"]) for s in stats] == [(2024, 42), (2025, 46)]
    assert sum(s["corrections"] for s in stats) == 6
    assert sum(s["positioned"] for s in stats) == 5
    assert sum(s["reinstall"] for s in stats) == 8
    assert count(runner, "SELECT count(*) FROM installation_report") == 42

    build = timeline_service(runner)
    pumps = [r["asset_code"] for r in baseline["asset_registry"] if r["asset_type"] == "PUMP"]
    eligible, intervals, positions, transitions, same_day, resolved = 0, 0, {}, 0, 0, 0
    for tag in pumps:
        svc = build(tag)
        result = svc.build_installation_based_mtbf(tag)
        eligible += bool(result.completed_interval_count)
        intervals += result.completed_interval_count
        transitions += len(result.non_comparable_transitions)
        same_day += len(result.excluded_intervals)
        for i in result.intervals:
            positions[i.position] = positions.get(i.position, 0) + 1
        resolved += svc.build_current_installation(tag, now=NOW).current.installation_status == STATUS_INSTALLED
    assert (eligible, intervals, round(100 * eligible / len(pumps), 2)) == (29, 36, 11.42)
    assert positions == {"PUMP_LEVEL": 35, "NDE": 1} and transitions == 5 and same_day == 0
    assert resolved == 39

    for tag, code, day, age in [("945-P-9B", "INSTL-026-2026", "2026-05-07", 143), ("211-P-1A", "INSTL-033-2026", "2026-05-22", 128),
                                ("140-P-26B", "INSTL-041-2026", "2026-06-07", 112), ("101-P-3B", "INSTL-025-2026", "2026-05-05", 145)]:
        current = build(tag).build_current_installation(tag, now=NOW).current
        assert (current.source_installation_code, current.installation_date, current.time_since_installation_days) == (code, day, age)
    assert build("701-P-1A").build_current_installation("701-P-1A", now=NOW).current.installation_status == "NOT_RECORDED"
