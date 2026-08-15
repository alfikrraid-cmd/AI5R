"""
MWO-LTSA-IMPORT-DIRECT-DB-001 -- proves DatabaseRunner's direct-connect
mode (config.host set -> psycopg2, no docker CLI/socket involved at
query/execute time) against a REAL Postgres, not a mock. This is the
mechanism the production api container now uses (compose.yaml's api
service sets AI5R_POSTGRES_HOST; dependencies.py's
_resolve_import_database_config() takes this branch whenever that var is
set); this test file is what actually exercises query_scalar()/
execute_script() over a real wire-protocol connection.

Disposable Postgres is spun up by this file's own fixture (`docker run`,
NOT `docker compose exec` -- the CLI here is the DEVELOPER/CI HOST'S own
docker, the same kind of host-side tooling `.env.verify.local`'s whole
disposable-stack convention already relies on elsewhere in this test
suite; this is not the api container using docker, which is exactly what
this MWO forbids and does not do). A published host port is required
so this test (running on the host, not inside any container) can open a
real TCP connection -- unlike compose.yaml's own `postgres` service,
which deliberately publishes no host port in production.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(INGESTION_PATH))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner  # noqa: E402

_CONTAINER_NAME = "ai5r-test-direct-connect-pg"
_USER = "ai5r"
_PASSWORD = "test-direct-connect-password"
_DATABASE = "ai5r_runtime"
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ltsa_pumps (
    tag_number VARCHAR(100) PRIMARY KEY,
    area VARCHAR(100),
    pump_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture(scope="module")
def direct_connect_runner():
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
            ["docker", "port", _CONTAINER_NAME, "5432/tcp"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        # e.g. "127.0.0.1:54321"
        host_port = int(port_output.rsplit(":", 1)[1])

        runner = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE)
        )

        # Poll with the REAL client this test actually needs (a live
        # psycopg2 connection), not pg_isready -- pg_isready can report
        # ready slightly before docker exec/cp against the same container
        # reliably succeeds, which was observed to flake here.
        last_error: Exception | None = None
        for _ in range(30):
            try:
                runner.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001 -- retry loop, re-raised below if never ready
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready for direct connections: {last_error}")

        # Written to a temp file and `docker cp`'d in, then applied via
        # `psql -f` -- NOT `subprocess.run(..., input=sql)` piped over
        # stdin: pytest's default fd-capture on Windows interferes with
        # subprocess stdin PIPE timing, causing psql to see a closed/empty
        # stdin and exit 2 even though the same call succeeds outside
        # pytest. Avoiding stdin entirely sidesteps this rather than
        # depending on every future test run passing -s.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False, encoding="utf-8") as handle:
            handle.write(_SCHEMA_SQL)
            schema_path = handle.name
        try:
            subprocess.run(
                ["docker", "cp", schema_path, f"{_CONTAINER_NAME}:/tmp/schema.sql"],
                check=True, capture_output=True, text=True,
            )
        finally:
            Path(schema_path).unlink(missing_ok=True)
        # The direct psycopg2 connection above already proved the server
        # accepts real connections; still retry `docker exec` itself a
        # few times since it is a separate, independently-flaky code path
        # from the actual connection this test exercises.
        schema_result = None
        for _ in range(5):
            schema_result = subprocess.run(
                [
                    "docker", "exec", _CONTAINER_NAME, "psql",
                    "-U", _USER, "-d", _DATABASE, "-v", "ON_ERROR_STOP=1", "-f", "/tmp/schema.sql",
                ],
                capture_output=True, text=True,
            )
            if schema_result.returncode == 0:
                break
            time.sleep(1)
        assert schema_result.returncode == 0, (
            f"schema apply failed rc={schema_result.returncode}\n"
            f"stdout={schema_result.stdout!r}\nstderr={schema_result.stderr!r}"
        )

        yield runner
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture(autouse=True)
def _clean_pumps(direct_connect_runner):
    direct_connect_runner.execute_script("DELETE FROM ltsa_pumps;")
    yield
    direct_connect_runner.execute_script("DELETE FROM ltsa_pumps;")


def test_direct_connect_mode_is_selected_only_when_host_is_set():
    docker_exec_config = DatabaseConfig(env_file=Path("x"), compose_file=Path("y"))
    assert docker_exec_config.host is None

    direct_config = DatabaseConfig(host="127.0.0.1", port=5432, user="u", password="p", database="d")
    assert direct_config.host == "127.0.0.1"


def test_query_scalar_reads_a_real_value_over_the_wire(direct_connect_runner):
    assert direct_connect_runner.query_scalar("SELECT count(*) FROM ltsa_pumps") == "0"


def test_execute_script_writes_a_real_row(direct_connect_runner):
    direct_connect_runner.execute_script(
        "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-1', 'Unit 1');"
    )
    assert direct_connect_runner.query_scalar(
        "SELECT area FROM ltsa_pumps WHERE tag_number = 'DC-TEST-1'"
    ) == "Unit 1"


def test_multi_statement_script_commits_atomically_on_success(direct_connect_runner):
    direct_connect_runner.execute_script(
        "BEGIN;"
        "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-2', 'Unit 2');"
        "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-3', 'Unit 3');"
        "COMMIT;"
    )
    assert direct_connect_runner.query_scalar("SELECT count(*) FROM ltsa_pumps") == "2"


def test_multi_statement_script_rolls_back_atomically_on_mid_script_failure(direct_connect_runner):
    # Same "-v ON_ERROR_STOP=1, nothing after a failure runs" semantics the
    # docker-exec/psql path already guaranteed -- the first INSERT below
    # must NOT survive the second statement's failure.
    with pytest.raises(Exception):
        direct_connect_runner.execute_script(
            "BEGIN;"
            "INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-ROLLBACK', 'Unit X');"
            "INSERT INTO this_table_does_not_exist VALUES (1);"
            "COMMIT;"
        )
    assert direct_connect_runner.query_scalar(
        "SELECT count(*) FROM ltsa_pumps WHERE tag_number = 'DC-TEST-ROLLBACK'"
    ) == "0"


def test_each_call_uses_its_own_connection_not_a_shared_leaked_one(direct_connect_runner):
    # No connection pooling/reuse -- confirms two independent calls both
    # succeed (a leaked/closed connection from the first call would break
    # the second), matching docker-exec mode's own "fresh process per call"
    # behavior.
    direct_connect_runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-4', 'Unit 4');")
    direct_connect_runner.execute_script("INSERT INTO ltsa_pumps (tag_number, area) VALUES ('DC-TEST-5', 'Unit 5');")
    assert direct_connect_runner.query_scalar("SELECT count(*) FROM ltsa_pumps") == "2"
