"""LTSA_PERTAMINA_RBAC_SCOPE_AND_REQUEST_R2 -- migration 055 + WorkRequestRepository
against a REAL, disposable Postgres (same pg_port / bootstrap_schema fixture
shape as test_condition_monitoring_reading_bulk_atomicity_real_db.py).

Proves: the table and its CHECK / FK constraints exist; a request creates
exactly one ltsa_work_request row and nothing in work_order / pm_occurrence /
cm_report / installation tables; the list honours ALL / AREA / empty scope.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.pump_area_scope import ALL_ASSETS_SCOPE  # noqa: E402
from API.work_request_repository import WorkRequestRepository  # noqa: E402

_CONTAINER_NAME = "ai5r-test-work-request-pg"
_USER = "ai5r"
_PASSWORD = "test-work-request-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATIONS = [
    _DATABASE_DIR / "MIGRATIONS" / "007_create_ltsa_auth_foundation.sql",
    _DATABASE_DIR / "MIGRATIONS" / "055_create_ltsa_work_request.sql",
]


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
        bootstrap_schema(probe, _SCHEMA_FILE)
        for migration in _MIGRATIONS:
            bootstrap_schema(probe, migration)
        # Idempotent: applying 055 a second time is a no-op.
        bootstrap_schema(probe, _MIGRATIONS[-1])
        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


_USER_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script("TRUNCATE ltsa_work_request, asset_registry, users CASCADE;")
    r.execute_script(
        f"INSERT INTO users (id, email, password_hash) VALUES ('{_USER_ID}', 'req@pertamina.test', 'x');"
        "INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) VALUES "
        "('104-P-HCC', '104-P-HCC', 'PUMP', 'HCC'), ('105-P-OM', '105-P-OM', 'PUMP', 'OM'), "
        "('211-P-1A', '211-P-1A', 'PUMP', 'REAKTOR');"
    )
    return r


def _count(runner, table):
    return int(runner.query_scalar(f"SELECT count(*) FROM {table}"))


def test_request_creates_only_a_work_request_row(runner):
    before = {
        t: _count(runner, t)
        for t in ("work_order", "pm_occurrence", "cm_report", "maintenance_history", "installation_report")
    }
    row = WorkRequestRepository(runner).create(
        request_type="CM", asset_code="104-P-HCC", description="Seal leak DE", requested_by=_USER_ID
    )
    assert row["request_code"].startswith("WR-")
    assert (row["request_type"], row["asset_code"], row["status"], row["requested_by"]) == ("CM", "104-P-HCC", "SUBMITTED", _USER_ID)
    assert _count(runner, "ltsa_work_request") == 1
    assert {t: _count(runner, t) for t in before} == before


@pytest.mark.parametrize(
    "bad_sql",
    [
        "('WR-1', 'REPAIR', '104-P-HCC', 'x', '{u}')",        # request_type CHECK
        "('WR-2', 'PM', 'NOT-AN-ASSET', 'x', '{u}')",         # asset FK
        "('WR-3', 'PM', '104-P-HCC', '   ', '{u}')",          # description CHECK
        "('WR-4', 'PM', '104-P-HCC', 'x', '44444444-4444-4444-4444-444444444444')",  # requester FK
    ],
)
def test_constraints_reject_invalid_requests(runner, bad_sql):
    with pytest.raises(Exception):
        runner.execute_script(
            "INSERT INTO ltsa_work_request (request_code, request_type, asset_code, description, requested_by) VALUES "
            + bad_sql.format(u=_USER_ID) + ";"
        )
    assert _count(runner, "ltsa_work_request") == 0


def test_status_cannot_be_anything_but_submitted(runner):
    with pytest.raises(Exception):
        runner.execute_script(
            "INSERT INTO ltsa_work_request (request_code, request_type, asset_code, description, requested_by, status) "
            f"VALUES ('WR-9', 'PM', '104-P-HCC', 'x', '{_USER_ID}', 'COMPLETED');"
        )


def test_list_honours_all_area_and_empty_scope(runner):
    repo = WorkRequestRepository(runner)
    for asset in ("104-P-HCC", "105-P-OM", "211-P-1A"):
        repo.create(request_type="PM", asset_code=asset, description="PM due", requested_by=_USER_ID)
    tags = lambda scope: sorted(r["asset_code"] for r in repo.list_requests(scope=scope))  # noqa: E731
    assert tags(None) == ["104-P-HCC", "105-P-OM", "211-P-1A"]
    assert tags(ALL_ASSETS_SCOPE) == ["104-P-HCC", "105-P-OM", "211-P-1A"]
    assert tags(frozenset({"HCC"})) == ["104-P-HCC"]
    assert tags(frozenset()) == []
