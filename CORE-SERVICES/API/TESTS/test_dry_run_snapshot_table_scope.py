"""
MWO-LTSA-IMPORT-PROD-SNAPSHOT-001 -- proves Pump XLSX dry-run no longer
fails against a production-equivalent, Pump-only database (ltsa_pumps +
import_sessions only -- no seal_registry/installation_report/seal_
engineering_document tables at all, matching the exact reported production
evidence).

Root cause: API/import_cli.py::_read_live_snapshot() unconditionally
queried all four entity tables (ltsa_pumps, seal_registry,
installation_report, seal_engineering_document) even though a Pump XLSX
dry-run's incoming package only ever has pumps -- parse_import_file() for
a Pump workbook never populates seals/installations/documents (see
import_cli.py's own module header). conflict_resolution.py's own
_compare_entity_type() loops over the INCOMING records only (`for
entity_id in sorted(incoming_by_key)`), so it never reads the database
snapshot for an entity type incoming has none of -- querying
installation_report for a Pump-only dry-run could never have changed the
result, and unconditionally querying it broke any deployment that has not
yet provisioned that table.

Fix: _read_live_snapshot(runner, incoming) now takes the incoming package
and queries each table only when `incoming` has at least one record of
that entity type. Not a new snapshot/importer engine, not a placeholder
table, not a validation change -- purely which SELECTs run.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

_API_PATH = Path(__file__).resolve().parents[1]
if str(_API_PATH) not in sys.path:
    sys.path.insert(0, str(_API_PATH))
_CORE_SERVICES_PATH = _API_PATH.parent
if str(_CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(_CORE_SERVICES_PATH))
_REPO_ROOT = _CORE_SERVICES_PATH.parent
_INGESTION_PATH = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner  # noqa: E402

from API.import_cli import dry_run_import  # noqa: E402
from API.import_session_repository import ImportSessionRepository  # noqa: E402

_CONTAINER_NAME = "ai5r-test-pump-only-snapshot-scope-pg"
_USER = "ai5r"
_PASSWORD = "test-snapshot-scope-password"
_DATABASE = "ltsa_brain"

# Exactly the reported production shape: ltsa_pumps (already migrated --
# MWO-LTSA-IMPORT-PROD-SCHEMA-001 -- with name/criticality) + import_sessions.
# Deliberately NO seal_registry, installation_report, or
# seal_engineering_document table at all -- this is the actual production
# gap this bug report describes, not simplified/guessed.
_PUMP_ONLY_SCHEMA_SQL = """
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
    name VARCHAR(255),
    criticality VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE import_sessions (
  session_id text PRIMARY KEY,
  status text NOT NULL,
  source text,
  created_at text,
  package jsonb NOT NULL,
  snapshot jsonb NOT NULL,
  execution_result jsonb,
  updated_at timestamptz DEFAULT now()
);
"""


@pytest.fixture(scope="module")
def pump_only_runner():
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

        runner = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE)
        )
        last_error: Exception | None = None
        for _ in range(30):
            try:
                runner.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready: {last_error}")

        runner.execute_script(_PUMP_ONLY_SCHEMA_SQL)
        yield runner
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture(autouse=True)
def _clean_pumps(pump_only_runner):
    pump_only_runner.execute_script("DELETE FROM ltsa_pumps; DELETE FROM import_sessions;")
    yield
    pump_only_runner.execute_script("DELETE FROM ltsa_pumps; DELETE FROM import_sessions;")


def _build_pump_workbook(tag_number: str) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Master Pump")
    ws.append(("Tag Number", "Area", "Pump Type"))
    ws.append((tag_number, "Unit 1", "OH2"))
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    return Path(tmp.name)


def test_querying_installation_report_directly_fails_on_this_pump_only_schema(pump_only_runner):
    # Proves the fixture faithfully reproduces the reported production gap
    # -- without this, a passing dry-run test below would prove nothing.
    with pytest.raises(Exception) as excinfo:
        pump_only_runner.query_scalar("SELECT installation_code FROM installation_report")
    assert "installation_report" in str(excinfo.value).lower()


def test_pump_xlsx_dry_run_succeeds_against_a_pump_only_production_schema(pump_only_runner):
    xlsx_path = _build_pump_workbook("SNAPSHOT-SCOPE-P-1")
    try:
        session_repository = ImportSessionRepository(runner=pump_only_runner)
        report = dry_run_import(xlsx_path, pump_only_runner, session_repository=session_repository)
    finally:
        xlsx_path.unlink(missing_ok=True)

    assert report.new_count == 1
    assert report.rejected_count == 0


def test_pump_xlsx_dry_run_writes_nothing_to_ltsa_pumps_on_pump_only_schema(pump_only_runner):
    count_before = pump_only_runner.query_scalar("SELECT count(*) FROM ltsa_pumps")

    xlsx_path = _build_pump_workbook("SNAPSHOT-SCOPE-P-2")
    try:
        session_repository = ImportSessionRepository(runner=pump_only_runner)
        dry_run_import(xlsx_path, pump_only_runner, session_repository=session_repository)
    finally:
        xlsx_path.unlink(missing_ok=True)

    count_after = pump_only_runner.query_scalar("SELECT count(*) FROM ltsa_pumps")
    assert count_before == count_after == "0"


def test_pump_xlsx_dry_run_session_persists_on_pump_only_schema(pump_only_runner):
    xlsx_path = _build_pump_workbook("SNAPSHOT-SCOPE-P-3")
    try:
        session_repository = ImportSessionRepository(runner=pump_only_runner)
        report = dry_run_import(xlsx_path, pump_only_runner, session_repository=session_repository)
    finally:
        xlsx_path.unlink(missing_ok=True)

    persisted = session_repository.get(report.session_id)
    assert persisted is not None
    assert persisted.status == "REVIEWING"
