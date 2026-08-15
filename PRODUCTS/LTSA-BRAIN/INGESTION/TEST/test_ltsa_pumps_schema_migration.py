"""
MWO-LTSA-IMPORT-PROD-SCHEMA-001 -- proves DATABASE/MIGRATIONS/006_ltsa_pumps_
add_name_criticality.sql (the idempotent `ALTER TABLE ltsa_pumps ADD COLUMN
IF NOT EXISTS name/criticality` already established by ADR-PUMP-001/
WO-PUMP-002 -- CANONICAL_SCHEMA.sql carries the identical two statements)
actually fixes the reported production failure:
`psycopg2.errors.UndefinedColumn: column "name" does not exist`.

Root cause: production's `ltsa_pumps` table predates WO-PUMP-002 -- it has
the pre-migration 14-column shape (id, tag_number, area, location,
pump_type, api_plan, seal_type, status, manufacturer, model, drawing_ref,
notes, created_at, updated_at), matching PRODUCTS/LTSA-BRAIN/MODULES/PUMP/
DATABASE/001_create_pumps.sql's CREATE TABLE with the name/criticality
lines removed -- reconstructed here from that evidence, not guessed.
Import's dry-run snapshot query (API/import_cli.py::_read_live_snapshot,
`SELECT {PUMP_CANONICAL_FIELDS} FROM ltsa_pumps`) selects name/criticality
unconditionally, so it fails against this older shape.

This file spins up a REAL, disposable, published-port Postgres (the same
`docker run` host-side pattern test_database_runner_direct_connect.py
already established), seeds it with EXACTLY the reported pre-migration
ltsa_pumps shape plus one real existing row (proving data preservation),
applies the migration via the existing bootstrap_schema()/DatabaseRunner.
execute_script() mechanism (ltsa_pump_inventory_db_upsert.py, reused
unmodified -- no new migration runner/engine is introduced), and then
exercises the real dry-run path end to end.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

_INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

_REPO_ROOT = _INGESTION_PATH.parents[2]
_CORE_SERVICES_PATH = _REPO_ROOT / "CORE-SERVICES"
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema, _json_query  # noqa: E402

from API.import_cli import dry_run_import  # noqa: E402
from API.import_session_repository import ImportSessionRepository  # noqa: E402

_CONTAINER_NAME = "ai5r-test-pump-schema-migration-pg"
_USER = "ai5r"
_PASSWORD = "test-schema-migration-password"
_DATABASE = "ltsa_brain"
_MIGRATION_FILE = (
    _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE" / "MIGRATIONS" / "006_ltsa_pumps_add_name_criticality.sql"
)

# Exactly the reported production shape: PRODUCTS/LTSA-BRAIN/MODULES/PUMP/
# DATABASE/001_create_pumps.sql's CREATE TABLE with the name/criticality
# lines removed -- the pre-WO-PUMP-002 shape, reconstructed from that real
# canonical source file, not invented.
_PRE_MIGRATION_LTSA_PUMPS_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE ltsa_pumps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_number VARCHAR(100) NOT NULL UNIQUE,
    area VARCHAR(100) NOT NULL,
    location VARCHAR(150),
    pump_type VARCHAR(100),
    api_plan VARCHAR(50),
    seal_type VARCHAR(150),
    status VARCHAR(50) DEFAULT 'UNKNOWN',
    manufacturer VARCHAR(150),
    model VARCHAR(150),
    drawing_ref TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Other tables Import's dry-run snapshot query reads (API/import_cli.py::
# _read_live_snapshot) -- minimal column-only stubs (no FKs/constraints,
# read-only in this test) so dry-run's OWN unrelated queries against these
# tables succeed; not part of this migration, not the bug being fixed.
_SUPPORTING_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS import_sessions (
  session_id text PRIMARY KEY,
  status text NOT NULL,
  source text,
  created_at text,
  package jsonb NOT NULL,
  snapshot jsonb NOT NULL,
  execution_result jsonb,
  updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS seal_registry (
    seal_code TEXT PRIMARY KEY,
    seal_name TEXT
);
CREATE TABLE IF NOT EXISTS installation_report (
    installation_code TEXT PRIMARY KEY,
    report_no TEXT,
    source_document_name TEXT
);
CREATE TABLE IF NOT EXISTS seal_engineering_document (
    document_code TEXT PRIMARY KEY,
    seal_code TEXT,
    document_type TEXT,
    title TEXT
);
"""

_EXISTING_ROW_TAG = "PROD-EXISTING-P-1"


def _run_sql_file(port: int, sql_text: str) -> None:
    runner = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    runner.execute_script(sql_text)


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", f"POSTGRES_USER={_USER}",
            "-e", f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e", f"POSTGRES_DB={_DATABASE}",
            "-p", "127.0.0.1::5432",
            "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _CONTAINER_NAME, "5432/tcp"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        host_port = int(port_output.rsplit(":", 1)[1])

        probe = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE)
        )
        last_error: Exception | None = None
        for _ in range(30):
            try:
                probe.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready: {last_error}")

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def pre_migration_runner(pg_port):
    """Fresh pre-WO-PUMP-002 schema for every test -- dropped and rebuilt
    each time so migration idempotency/data-preservation checks never leak
    state between tests."""
    runner = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    runner.execute_script("DROP TABLE IF EXISTS ltsa_pumps;")
    runner.execute_script(_PRE_MIGRATION_LTSA_PUMPS_SQL)
    runner.execute_script(_SUPPORTING_TABLES_SQL)
    runner.execute_script(
        f"INSERT INTO ltsa_pumps (tag_number, area, pump_type, status) "
        f"VALUES ('{_EXISTING_ROW_TAG}', 'Unit 1', 'OH2', 'ACTIVE');"
    )
    return runner


def _column_names(runner: DatabaseRunner) -> set[str]:
    rows = _json_query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'ltsa_pumps'", runner
    )
    return {row["column_name"] for row in rows}


def test_reported_bug_is_reproduced_before_migration(pre_migration_runner):
    # Proves the test fixture actually recreates the real production
    # failure -- without this, a passing post-migration test would prove
    # nothing.
    with pytest.raises(Exception) as excinfo:
        pre_migration_runner.query_scalar("SELECT name FROM ltsa_pumps")
    assert "name" in str(excinfo.value).lower()


def test_migration_adds_missing_columns_without_dropping_existing_ones(pre_migration_runner):
    before = _column_names(pre_migration_runner)
    assert "name" not in before
    assert "criticality" not in before

    bootstrap_schema(pre_migration_runner, _MIGRATION_FILE)

    after = _column_names(pre_migration_runner)
    assert "name" in after
    assert "criticality" in after
    # Nothing removed -- every pre-migration column is still present.
    assert before <= after


def test_migration_preserves_existing_production_rows(pre_migration_runner):
    bootstrap_schema(pre_migration_runner, _MIGRATION_FILE)

    rows = _json_query(
        f"SELECT tag_number, area, pump_type, status, name, criticality FROM ltsa_pumps "
        f"WHERE tag_number = '{_EXISTING_ROW_TAG}'",
        pre_migration_runner,
    )
    assert rows == [
        {
            "tag_number": _EXISTING_ROW_TAG,
            "area": "Unit 1",
            "pump_type": "OH2",
            "status": "ACTIVE",
            "name": None,
            "criticality": None,
        }
    ]


def test_migration_is_idempotent_when_rerun(pre_migration_runner):
    bootstrap_schema(pre_migration_runner, _MIGRATION_FILE)
    # Second application must not raise (ADD COLUMN IF NOT EXISTS) and
    # must not duplicate/alter anything already there.
    bootstrap_schema(pre_migration_runner, _MIGRATION_FILE)

    rows = _json_query(
        f"SELECT tag_number FROM ltsa_pumps WHERE tag_number = '{_EXISTING_ROW_TAG}'", pre_migration_runner
    )
    assert len(rows) == 1


def _build_pump_workbook(tag_number: str) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Master Pump")
    ws.append(("Tag Number", "Area", "Pump Type"))
    ws.append((tag_number, "Unit 2", "OH2"))
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    return Path(tmp.name)


def test_dry_run_succeeds_after_migration_with_zero_writes_and_session_persisted(pre_migration_runner):
    bootstrap_schema(pre_migration_runner, _MIGRATION_FILE)

    count_before = pre_migration_runner.query_scalar("SELECT count(*) FROM ltsa_pumps")

    xlsx_path = _build_pump_workbook("PROD-NEW-P-2")
    try:
        session_repository = ImportSessionRepository(runner=pre_migration_runner)
        report = dry_run_import(xlsx_path, pre_migration_runner, session_repository=session_repository)
    finally:
        xlsx_path.unlink(missing_ok=True)

    # Dry-run succeeded (no UndefinedColumn) and classified the new tag.
    assert report.new_count == 1

    # Zero writes to ltsa_pumps: row count is unchanged (still just the
    # one pre-existing row) -- dry-run never calls execute_import().
    count_after = pre_migration_runner.query_scalar("SELECT count(*) FROM ltsa_pumps")
    assert count_after == count_before == "1"

    # Session persisted durably (import_sessions), reachable via the same
    # repository the API's own GET .../status endpoint uses.
    persisted = session_repository.get(report.session_id)
    assert persisted is not None
    assert persisted.status == "REVIEWING"
