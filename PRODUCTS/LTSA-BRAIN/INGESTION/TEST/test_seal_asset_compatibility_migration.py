"""MWO-LTSA-ASSET-SEAL-COMPATIBILITY-001 regression tests."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_INGESTION_PATH = Path(__file__).resolve().parents[1]
if str(_INGESTION_PATH) not in sys.path:
    sys.path.insert(0, str(_INGESTION_PATH))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query, bootstrap_schema  # noqa: E402

_REPO_ROOT = _INGESTION_PATH.parents[2]
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATION_024 = _DATABASE_DIR / "MIGRATIONS" / "024_create_seal_pump_compatibility_history.sql"
_MIGRATION_025 = _DATABASE_DIR / "MIGRATIONS" / "025_retarget_seal_pump_compatibility_to_asset_registry.sql"

_CONTAINER_NAME = "ai5r-test-seal-asset-compatibility-pg"
_USER = "ai5r"
_PASSWORD = "test-seal-asset-compatibility-password"
_DATABASE = "ltsa_brain"


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", f"POSTGRES_USER={_USER}",
            "-e", f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e", f"POSTGRES_DB={_DATABASE}",
            "-p", "127.0.0.1::5432", "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _CONTAINER_NAME, "5432/tcp"], check=True, capture_output=True, text=True
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
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        """
        DO $$
        DECLARE obj record;
        BEGIN
            FOR obj IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', obj.tablename);
            END LOOP;
        END $$;
        """
    )
    bootstrap_schema(r, _SCHEMA_FILE)
    bootstrap_schema(r, _MIGRATION_024)
    return r


def _seed_current_projection_shape(runner: DatabaseRunner) -> None:
    runner.execute_script(
        """
        INSERT INTO public.ltsa_pumps (tag_number, area, pump_type)
        VALUES
            ('110-P-9A', 'HOC', 'OH'),
            ('101-LRC-102', 'CDU', 'LIQUID RING COMPRESSOR'),
            ('701-MM-51', 'H2Plan', 'OH2'),
            ('702-MM-51', 'H2Plan', 'OH2');

        INSERT INTO public.asset_registry (asset_code, asset_name, asset_type, area)
        VALUES
            ('110-P-9A', '110-P-9A', 'PUMP', 'HOC'),
            ('101-LRC-102', '101-LRC-102', 'LIQUID RING COMPRESSOR', 'CDU'),
            ('701-MM-51', '701-MM-51', NULL, 'H2Plan'),
            ('702-MM-51', '702-MM-51', NULL, 'H2Plan');

        INSERT INTO public.seal_registry (seal_code, seal_name, status)
        VALUES
            ('S-PUMP', 'Pump Seal', 'ACTIVE'),
            ('S-LRC', 'LRC Seal', 'ACTIVE'),
            ('S-MM', 'MM Seal', 'ACTIVE'),
            ('S-946', 'Retired 946 Seal', 'ACTIVE');

        INSERT INTO public.seal_stock (seal_code, quantity_on_hand)
        VALUES ('S-PUMP', 2);

        INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number, notes)
        VALUES
            ('S-PUMP', '110-P-9A', 'pump evidence'),
            ('S-LRC', '101-LRC-102', 'HSC & SPK'),
            ('S-MM', '701-MM-51', 'HCC'),
            ('S-MM', '702-MM-51', 'HCC');

        INSERT INTO public.seal_pump_compatibility_history (
            seal_code, original_pump_tag_number, original_compatibility_key,
            original_notes, retirement_reason
        )
        VALUES (
            'S-946', '946-P-2D', 'S-946::946-P-2D',
            'HSC & SPK', 'RETIRED_NONCANONICAL_PUMP_TAG'
        );
        """
    )


def _constraints(runner: DatabaseRunner) -> list[dict]:
    return _json_query(
        """
        SELECT conname, pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE conrelid = 'public.seal_pump_compatibility'::regclass
        ORDER BY conname
        """,
        runner,
    )


def test_migration_retargets_active_compatibility_to_asset_registry_and_preserves_evidence(runner):
    _seed_current_projection_shape(runner)

    bootstrap_schema(runner, _MIGRATION_025)

    constraints = _constraints(runner)
    assert any(
        row["conname"] == "seal_pump_compatibility_asset_code_fkey"
        and "REFERENCES asset_registry(asset_code)" in row["definition"]
        for row in constraints
    )
    assert not any("REFERENCES ltsa_pumps(tag_number)" in row["definition"] for row in constraints)
    assert any("FOREIGN KEY (seal_code) REFERENCES seal_registry(seal_code)" in row["definition"] for row in constraints)

    rows = _json_query(
        "SELECT seal_code, pump_tag_number, notes FROM public.seal_pump_compatibility "
        "ORDER BY pump_tag_number, seal_code",
        runner,
    )
    assert rows == [
        {"seal_code": "S-LRC", "pump_tag_number": "101-LRC-102", "notes": "HSC & SPK"},
        {"seal_code": "S-PUMP", "pump_tag_number": "110-P-9A", "notes": "pump evidence"},
        {"seal_code": "S-MM", "pump_tag_number": "701-MM-51", "notes": "HCC"},
        {"seal_code": "S-MM", "pump_tag_number": "702-MM-51", "notes": "HCC"},
    ]

    assert runner.query_scalar("SELECT count(*) FROM public.seal_registry") == "4"
    assert runner.query_scalar("SELECT count(*) FROM public.seal_stock") == "1"
    assert runner.query_scalar("SELECT count(*) FROM public.seal_pump_compatibility_history") == "1"


def test_non_pump_assets_can_leave_ltsa_pumps_without_losing_active_compatibility(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_025)

    runner.execute_script(
        """
        DELETE FROM public.ltsa_pumps
        WHERE tag_number IN ('101-LRC-102', '701-MM-51', '702-MM-51');
        """
    )

    assert runner.query_scalar(
        "SELECT count(*) FROM public.ltsa_pumps WHERE tag_number IN ('101-LRC-102','701-MM-51','702-MM-51')"
    ) == "0"
    assert runner.query_scalar(
        "SELECT count(*) FROM public.asset_registry WHERE asset_code IN ('101-LRC-102','701-MM-51','702-MM-51')"
    ) == "3"
    assert runner.query_scalar(
        "SELECT count(*) FROM public.seal_pump_compatibility "
        "WHERE pump_tag_number IN ('101-LRC-102','701-MM-51','702-MM-51')"
    ) == "3"


def test_active_compatibility_requires_existing_asset_and_existing_seal(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_025)

    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script(
            """
            INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number)
            VALUES ('S-PUMP', 'MISSING-ASSET');
            """
        )
    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script(
            """
            INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number)
            VALUES ('MISSING-SEAL', '110-P-9A');
            """
        )
    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script("DELETE FROM public.asset_registry WHERE asset_code = '101-LRC-102';")


def test_migration_is_idempotent_and_does_not_duplicate_compatibility(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_025)
    bootstrap_schema(runner, _MIGRATION_025)

    assert runner.query_scalar("SELECT count(*) FROM public.seal_pump_compatibility") == "4"
    assert runner.query_scalar(
        "SELECT count(*) FROM ("
        "SELECT seal_code, pump_tag_number FROM public.seal_pump_compatibility "
        "GROUP BY seal_code, pump_tag_number"
        ") unique_rows"
    ) == "4"
    assert runner.query_scalar(
        "SELECT count(*) FROM public.seal_pump_compatibility_history "
        "WHERE original_pump_tag_number = '946-P-2D'"
    ) == "1"
