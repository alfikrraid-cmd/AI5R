"""MWO-LTSA-LEGACY-SEAL-COMPATIBILITY-EVIDENCE-001 regression tests."""

from __future__ import annotations

import subprocess
import sys
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

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, _json_query, bootstrap_schema  # noqa: E402
from API.seal_pump_compatibility_retirement_service import (  # noqa: E402
    SealPumpCompatibilityRetirementService,
)

_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATION_024 = _DATABASE_DIR / "MIGRATIONS" / "024_create_seal_pump_compatibility_history.sql"

_CONTAINER_NAME = "ai5r-test-legacy-seal-compatibility-pg"
_USER = "ai5r"
_PASSWORD = "test-legacy-seal-compatibility-password"
_DATABASE = "ltsa_brain"


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            _CONTAINER_NAME,
            "-e",
            f"POSTGRES_USER={_USER}",
            "-e",
            f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e",
            f"POSTGRES_DB={_DATABASE}",
            "-p",
            "127.0.0.1::5432",
            "postgres:16-alpine",
        ],
        check=True,
        capture_output=True,
        text=True,
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
            FOR obj IN
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', obj.tablename);
            END LOOP;
        END $$;
        """
    )
    bootstrap_schema(r, _SCHEMA_FILE)
    bootstrap_schema(r, _MIGRATION_024)
    return r


def _seed_canonical_context(runner: DatabaseRunner) -> None:
    runner.execute_script(
        """
        INSERT INTO public.ltsa_pumps (tag_number, area, pump_type)
        VALUES
            ('946-P-2D', 'OM 2', 'OH'),
            ('251-P-1A', 'S_PAKNING', 'OH');

        INSERT INTO public.seal_registry (seal_code, seal_name, status)
        VALUES
            ('LTSA-SEAL-T48MP-T909-2-3-8', 'T48MP / T909', 'ACTIVE'),
            ('LTSA-SEAL-5610VQ-2-1-4', '5610VQ', 'ACTIVE');

        INSERT INTO public.seal_stock (seal_code, quantity_on_hand)
        VALUES ('LTSA-SEAL-T48MP-T909-2-3-8', 0);

        INSERT INTO public.asset_registry (asset_code, asset_name, asset_type)
        VALUES ('101-LRC-102', '101-LRC-102', 'LIQUID RING COMPRESSOR');
        """
    )


def _active_count(runner: DatabaseRunner, seal_code: str, pump_tag_number: str) -> int:
    return int(
        runner.query_scalar(
            "SELECT count(*) FROM public.seal_pump_compatibility "
            f"WHERE seal_code = '{seal_code}' AND pump_tag_number = '{pump_tag_number}'"
        )
    )


def test_migration_preserves_active_fk_and_history_uses_original_pump_text(runner):
    _seed_canonical_context(runner)
    runner.execute_script(
        """
        INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number, notes)
        VALUES ('LTSA-SEAL-T48MP-T909-2-3-8', '946-P-2D', 'HSC & SPK');
        """
    )

    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script(
            """
            INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number, notes)
            VALUES ('LTSA-SEAL-T48MP-T909-2-3-8', '946-P-4A', 'HSC & SPK');
            """
        )

    runner.execute_script("DELETE FROM public.seal_pump_compatibility WHERE pump_tag_number = '946-P-2D';")
    runner.execute_script("DELETE FROM public.ltsa_pumps WHERE tag_number = '946-P-2D';")
    runner.execute_script(
        """
        INSERT INTO public.seal_pump_compatibility_history (
            seal_code,
            original_pump_tag_number,
            original_compatibility_key,
            original_notes,
            retirement_reason
        )
        VALUES (
            'LTSA-SEAL-T48MP-T909-2-3-8',
            '946-P-2D',
            'LTSA-SEAL-T48MP-T909-2-3-8::946-P-2D',
            'HSC & SPK',
            'RETIRED_NONCANONICAL_PUMP_TAG'
        );
        """
    )

    assert runner.query_scalar("SELECT count(*) FROM public.seal_pump_compatibility_history") == "1"
    with pytest.raises(Exception):  # noqa: B017
        runner.execute_script(
            """
            INSERT INTO public.seal_pump_compatibility_history (
                seal_code, original_pump_tag_number, original_compatibility_key, retirement_reason
            )
            VALUES ('MISSING-SEAL', '946-P-4A', 'MISSING-SEAL::946-P-4A', 'RETIRED_NONCANONICAL_PUMP_TAG');
            """
        )


def test_retirement_is_atomic_lossless_idempotent_and_isolated(runner):
    _seed_canonical_context(runner)
    runner.execute_script(
        """
        INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number, notes)
        VALUES
            ('LTSA-SEAL-T48MP-T909-2-3-8', '946-P-2D', 'HSC & SPK'),
            ('LTSA-SEAL-T48MP-T909-2-3-8', '251-P-1A', 'KEEP ACTIVE');
        """
    )

    service = SealPumpCompatibilityRetirementService(runner)
    result = service.retire(
        seal_code="LTSA-SEAL-T48MP-T909-2-3-8",
        pump_tag_number="946-P-2D",
        retirement_reason="RETIRED_NONCANONICAL_PUMP_TAG",
        retired_by="test-suite",
        source_reference="projection-prod-20260817.json",
    )

    assert result is not None
    assert result["seal_code"] == "LTSA-SEAL-T48MP-T909-2-3-8"
    assert result["original_pump_tag_number"] == "946-P-2D"
    assert result["original_compatibility_key"] == "LTSA-SEAL-T48MP-T909-2-3-8::946-P-2D"
    assert result["original_notes"] == "HSC & SPK"
    assert result["source_reference"] == "projection-prod-20260817.json"
    assert result["retirement_reason"] == "RETIRED_NONCANONICAL_PUMP_TAG"
    assert result["retired_by"] == "test-suite"
    assert _active_count(runner, "LTSA-SEAL-T48MP-T909-2-3-8", "946-P-2D") == 0
    assert _active_count(runner, "LTSA-SEAL-T48MP-T909-2-3-8", "251-P-1A") == 1

    again = service.retire(
        seal_code="LTSA-SEAL-T48MP-T909-2-3-8",
        pump_tag_number="946-P-2D",
        retirement_reason="RETIRED_NONCANONICAL_PUMP_TAG",
        retired_by="test-suite",
    )

    assert again is not None
    assert again["compatibility_history_id"] == result["compatibility_history_id"]
    assert runner.query_scalar("SELECT count(*) FROM public.seal_pump_compatibility_history") == "1"
    assert runner.query_scalar("SELECT count(*) FROM public.seal_registry") == "2"
    assert runner.query_scalar("SELECT count(*) FROM public.seal_stock") == "1"
    assert runner.query_scalar("SELECT count(*) FROM public.asset_registry") == "1"
    assert runner.query_scalar("SELECT count(*) FROM public.ltsa_pumps") == "2"


def test_history_insert_failure_rolls_back_active_delete(runner):
    _seed_canonical_context(runner)
    runner.execute_script(
        """
        INSERT INTO public.seal_pump_compatibility (seal_code, pump_tag_number, notes)
        VALUES ('LTSA-SEAL-T48MP-T909-2-3-8', '946-P-2D', 'HSC & SPK');
        ALTER TABLE public.seal_pump_compatibility_history
            ADD CONSTRAINT reject_test_reason CHECK (retirement_reason <> 'FAIL_INSERT');
        """
    )

    service = SealPumpCompatibilityRetirementService(runner)
    with pytest.raises(Exception):  # noqa: B017
        service.retire(
            seal_code="LTSA-SEAL-T48MP-T909-2-3-8",
            pump_tag_number="946-P-2D",
            retirement_reason="FAIL_INSERT",
            retired_by="test-suite",
        )

    assert _active_count(runner, "LTSA-SEAL-T48MP-T909-2-3-8", "946-P-2D") == 1
    assert runner.query_scalar("SELECT count(*) FROM public.seal_pump_compatibility_history") == "0"


def test_retirement_service_does_not_expose_generic_history_mutations():
    service_methods = {name for name in dir(SealPumpCompatibilityRetirementService) if not name.startswith("_")}
    assert service_methods == {"retire"}
