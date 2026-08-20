"""MWO-LTSA-PM-CMON-SCHEMA-CLOSURE-001 -- proves the committed PM/CMON
schema can bootstrap cleanly and can upgrade a legacy deployment where the
PM/CMON base tables are absent before migrations 014/015 are applied.
"""

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
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATION_014 = _DATABASE_DIR / "MIGRATIONS" / "014_alter_pm_cmon_workflow_and_evidence.sql"
_MIGRATION_015 = _DATABASE_DIR / "MIGRATIONS" / "015_alter_historical_pm_cmon_ingestion.sql"
_MIGRATION_023 = _DATABASE_DIR / "MIGRATIONS" / "023_create_pm_cmon_base_tables_for_legacy_upgrade.sql"

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema, _json_query  # noqa: E402

_CONTAINER_NAME = "ai5r-test-pm-cmon-schema-closure-pg"
_USER = "ai5r"
_PASSWORD = "test-pm-cmon-schema-closure-password"
_DATABASE = "ltsa_brain"

_PM_EXPECTED_COLUMNS = {
    "pm_occurrence_code",
    "pm_schedule_code",
    "asset_code",
    "asset_type",
    "occurrence_date",
    "status",
    "checklist_completion",
    "work_order_code",
    "activities",
    "finding",
    "preliminary_recommendation",
    "remarks",
    "provenance",
    "workflow_status",
    "source_reference",
    "source_workbook_name",
    "source_sheet_name",
    "source_row_number",
}

_CMON_EXPECTED_COLUMNS = {
    "condition_monitoring_reading_code",
    "condition_monitoring_schedule_code",
    "asset_code",
    "asset_type",
    "reading_date",
    "flushing_temp_de",
    "flushing_temp_nde",
    "mechanical_seal_leak_de",
    "mechanical_seal_leak_nde",
    "suction_pressure",
    "discharge_pressure",
    "stuffing_box_temp_de",
    "stuffing_box_temp_nde",
    "seal_gland_temp_de",
    "seal_gland_temp_nde",
    "vertical_vibration_de",
    "vertical_vibration_nde",
    "horizontal_vibration_de",
    "horizontal_vibration_nde",
    "axial_vibration_de",
    "axial_vibration_nde",
    "bearing_temp_de",
    "bearing_temp_nde",
    "motor_current",
    "finding",
    "provenance",
    "workflow_status",
    "source_reference",
    "source_workbook_name",
    "source_sheet_name",
    "source_row_number",
}


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
    return r


def _columns(runner: DatabaseRunner, table_name: str) -> list[str]:
    return [
        row["column_name"]
        for row in _json_query(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}' "
            "ORDER BY ordinal_position",
            runner,
        )
    ]


def _table_count(runner: DatabaseRunner, table_name: str) -> int:
    return int(
        runner.query_scalar(
            "SELECT count(*) FROM information_schema.tables "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}'"
        )
    )


def _apply_pm_cmon_upgrade_chain(runner: DatabaseRunner) -> None:
    bootstrap_schema(runner, _MIGRATION_023)
    bootstrap_schema(runner, _MIGRATION_014)
    bootstrap_schema(runner, _MIGRATION_015)


def test_canonical_schema_has_no_duplicate_condition_monitoring_asset_code(runner):
    bootstrap_schema(runner, _SCHEMA_FILE)
    assert _columns(runner, "condition_monitoring_reading").count("asset_code") == 1


def test_clean_bootstrap_creates_final_pm_cmon_contract(runner):
    bootstrap_schema(runner, _SCHEMA_FILE)
    assert _PM_EXPECTED_COLUMNS <= set(_columns(runner, "pm_occurrence"))
    cmon_columns = _columns(runner, "condition_monitoring_reading")
    assert _CMON_EXPECTED_COLUMNS <= set(cmon_columns)
    assert cmon_columns.count("asset_code") == 1


def test_legacy_missing_pm_cmon_tables_upgrade_before_014_015(runner):
    runner.execute_script(
        """
        CREATE TABLE public.ltsa_pumps (
            tag_number VARCHAR(100) PRIMARY KEY,
            area VARCHAR(100) NOT NULL
        );
        CREATE TABLE public.document_field_extraction (
            document_field_extraction_id TEXT PRIMARY KEY NOT NULL,
            source_document_id TEXT NOT NULL,
            source_document_type TEXT NOT NULL,
            detected_document_type TEXT NOT NULL,
            extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'
        );
        CREATE TABLE public.pdf_document (
            pdf_document_id TEXT PRIMARY KEY NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            CONSTRAINT pdf_document_type_check CHECK (document_type IN ('INSTALLATION_REPORT'))
        );
        CREATE TABLE public.cm_report (
            cm_report_code TEXT PRIMARY KEY NOT NULL,
            asset_code TEXT,
            asset_type TEXT,
            failure_category TEXT NOT NULL,
            severity TEXT NOT NULL,
            failure_description TEXT NOT NULL
        );
        INSERT INTO public.ltsa_pumps (tag_number, area) VALUES ('140-P-3A', 'HSC');
        """
    )

    _apply_pm_cmon_upgrade_chain(runner)

    assert _table_count(runner, "pm_occurrence") == 1
    assert _table_count(runner, "condition_monitoring_reading") == 1
    assert _table_count(runner, "pm_cm_evidence") == 1
    assert _PM_EXPECTED_COLUMNS <= set(_columns(runner, "pm_occurrence"))
    cmon_columns = _columns(runner, "condition_monitoring_reading")
    assert _CMON_EXPECTED_COLUMNS <= set(cmon_columns)
    assert cmon_columns.count("asset_code") == 1
    assert runner.query_scalar("SELECT count(*) FROM ltsa_pumps") == "1"


def test_already_current_database_preserves_pm_cmon_rows_on_rerun(runner):
    bootstrap_schema(runner, _SCHEMA_FILE)
    runner.execute_script(
        """
        INSERT INTO public.pm_occurrence
            (pm_occurrence_code, pm_schedule_code, asset_code, asset_type, occurrence_date, remarks)
        VALUES
            ('PMOCC-KEEP', 'PMS-KEEP', '140-P-3A', 'PUMP', '2026-07-01', 'preserve me');

        INSERT INTO public.condition_monitoring_reading
            (condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, asset_type, reading_date, finding)
        VALUES
            ('CMONR-KEEP', 'CMS-KEEP', '140-P-3A', 'PUMP', '2026-07-02', 'preserve me');
        """
    )

    _apply_pm_cmon_upgrade_chain(runner)
    _apply_pm_cmon_upgrade_chain(runner)

    assert runner.query_scalar("SELECT count(*) FROM pm_occurrence") == "1"
    assert runner.query_scalar("SELECT remarks FROM pm_occurrence WHERE pm_occurrence_code = 'PMOCC-KEEP'") == "preserve me"
    assert runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") == "1"
    assert (
        runner.query_scalar(
            "SELECT finding FROM condition_monitoring_reading WHERE condition_monitoring_reading_code = 'CMONR-KEEP'"
        )
        == "preserve me"
    )
    assert _columns(runner, "condition_monitoring_reading").count("asset_code") == 1


def test_pm_cmon_closure_sql_introduces_no_destructive_statements():
    sql = _MIGRATION_023.read_text(encoding="utf-8").upper()
    assert "DROP TABLE" not in sql
    assert "TRUNCATE" not in sql
    assert "DELETE FROM" not in sql
