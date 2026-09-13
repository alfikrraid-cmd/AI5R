"""MWO-LTSA-CM-R2 regression tests for migration 035 -- retargets
document_field_extraction.pump_tag_number's FK from ltsa_pumps(tag_number)
to asset_registry(asset_code), mirroring migration 025's own established
pattern (test_seal_asset_compatibility_migration.py) for the exact same
principle applied to a second table."""

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
_MIGRATION_035 = _DATABASE_DIR / "MIGRATIONS" / "035_retarget_document_field_extraction_to_asset_registry.sql"

_CONTAINER_NAME = "ai5r-test-document-field-extraction-asset-pg"
_USER = "ai5r"
_PASSWORD = "test-document-field-extraction-asset-password"
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
    return r


def _seed_current_projection_shape(runner: DatabaseRunner) -> None:
    """Mirrors migration 025's test fixture verbatim: seed the CURRENT
    (pre-migration) projection shape, where a non-pump asset can only
    have an extraction row today because it is ALSO (incidentally, not
    semantically) present in ltsa_pumps -- the exact bug this migration
    fixes. Deleting it from ltsa_pumps afterward (a separate test) is
    what actually proves independence, not the seed step itself."""
    runner.execute_script(
        """
        INSERT INTO public.ltsa_pumps (tag_number, area, pump_type)
        VALUES
            ('110-P-9A', 'HOC', 'OH'),
            ('701-MM-51', 'H2Plan', 'OH2'),
            ('101-LRC-102', 'CDU', 'LIQUID RING COMPRESSOR');

        INSERT INTO public.asset_registry (asset_code, asset_name, asset_type, area)
        VALUES
            ('110-P-9A', '110-P-9A', 'PUMP', 'HOC'),
            ('701-MM-51', '701-MM-51', NULL, 'H2Plan'),
            ('101-LRC-102', '101-LRC-102', 'LIQUID RING COMPRESSOR', 'CDU');

        INSERT INTO public.document_field_extraction (
            document_field_extraction_id, source_document_id, source_document_type,
            detected_document_type, pump_tag_number
        )
        VALUES
            ('DFE-1', 'SRC-1', 'PDF', 'HISTORICAL_CMON_READING_CANDIDATE', '110-P-9A'),
            ('DFE-2', 'SRC-1', 'PDF', 'HISTORICAL_CMON_READING_CANDIDATE', '701-MM-51'),
            ('DFE-3', 'SRC-1', 'PDF', 'HISTORICAL_PM_OCCURRENCE_CANDIDATE', '101-LRC-102');
        """
    )


def _constraints(runner: DatabaseRunner) -> list[dict]:
    return _json_query(
        """
        SELECT conname, pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE conrelid = 'public.document_field_extraction'::regclass
        ORDER BY conname
        """,
        runner,
    )


def test_migration_retargets_fk_to_asset_registry_and_preserves_rows(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_035)

    constraints = _constraints(runner)
    assert any(
        row["conname"] == "document_field_extraction_asset_code_fkey"
        and "REFERENCES asset_registry(asset_code)" in row["definition"]
        for row in constraints
    )
    assert not any("REFERENCES ltsa_pumps(tag_number)" in row["definition"] for row in constraints)

    assert runner.query_scalar("SELECT count(*) FROM public.document_field_extraction") == "3"


def test_non_pump_asset_extraction_survives_removal_from_ltsa_pumps(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_035)

    # The actual independence proof: removing the motor/compressor from
    # ltsa_pumps (where they should never have needed to be) must NOT
    # cascade-delete or orphan their extraction rows, now that the FK
    # targets asset_registry instead.
    runner.execute_script(
        "DELETE FROM public.ltsa_pumps WHERE tag_number IN ('701-MM-51', '101-LRC-102');"
    )

    assert runner.query_scalar(
        "SELECT count(*) FROM public.ltsa_pumps WHERE tag_number IN ('701-MM-51','101-LRC-102')"
    ) == "0"
    assert runner.query_scalar(
        "SELECT count(*) FROM public.document_field_extraction WHERE pump_tag_number IN ('701-MM-51','101-LRC-102')"
    ) == "2"


def test_new_extraction_row_requires_existing_asset_registry_entry(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_035)

    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script(
            """
            INSERT INTO public.document_field_extraction (
                document_field_extraction_id, source_document_id, source_document_type,
                detected_document_type, pump_tag_number
            )
            VALUES ('DFE-BAD', 'SRC-1', 'PDF', 'HISTORICAL_CMON_READING_CANDIDATE', 'MISSING-ASSET');
            """
        )


def test_migration_is_idempotent(runner):
    _seed_current_projection_shape(runner)
    bootstrap_schema(runner, _MIGRATION_035)
    bootstrap_schema(runner, _MIGRATION_035)

    assert runner.query_scalar("SELECT count(*) FROM public.document_field_extraction") == "3"
    constraints = _constraints(runner)
    asset_fk_count = sum(1 for row in constraints if row["conname"] == "document_field_extraction_asset_code_fkey")
    assert asset_fk_count == 1
