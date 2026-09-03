"""MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- Section 13 simulated end-to-end:
540 PENDING_REVIEW candidates -> exact bulk review -> 540 REVIEWED ->
exact atomic batch promotion -> 540 SAVED + 540 real pm_occurrence rows,
against a real, disposable Postgres running the actual canonical schema
(same discipline as test_pm_occurrence_repository_real_db.py). Then a
verbatim rerun of the same promotion request proves PM_DELTA_ON_RERUN=0
(idempotent, no duplicate rows) against a real database, not a Fake.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
_BACKEND_API_DIR = _CORE_SERVICES_DIR / "BACKEND-API"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR, _BACKEND_API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.pm_occurrence_repository import PMOccurrenceRepository  # noqa: E402
from API.historical_pm_cmon_staging_repository import HistoricalPMCMONStagingRepository  # noqa: E402
from API.historical_bulk_review_service import bulk_review_candidates  # noqa: E402
from API.historical_pm_promotion_batch_service import promote_pm_batch  # noqa: E402

_CONTAINER_NAME = "ai5r-test-pm-promotion-e2e-pg"
_USER = "ai5r"
_PASSWORD = "test-pm-promotion-e2e-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATIONS = [
    _DATABASE_DIR / "MIGRATIONS" / name
    for name in (
        "007_create_ltsa_auth_foundation.sql",
        "008_create_internal_component_inventory.sql",
        "009_create_installation_report.sql",
        "010_alter_document_field_extraction_review_provenance.sql",
        "011_alter_installation_report_post_installation_readings.sql",
        "012_alter_auth_foundation_attribution.sql",
        "013_alter_seal_registry_identifiers_attribution.sql",
        "014_alter_pm_cmon_workflow_and_evidence.sql",
        "015_alter_historical_pm_cmon_ingestion.sql",
        "016_alter_organization_membership_data_scope.sql",
        "017_create_record_change_history.sql",
        "023_create_pm_cmon_base_tables_for_legacy_upgrade.sql",
        "027_add_pm_cmon_soft_delete.sql",
        "028_add_schedule_attribution_soft_delete.sql",
    )
]

_ASSET_CODE = "211-P-13AR"
_ACTOR = "22222222-2222-2222-2222-222222222222"
_N = 540


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

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE pm_occurrence, pm_schedule, document_field_extraction, record_change_history, "
        "ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_ASSET_CODE}', 'HOC');")

    rows = []
    base_date = date(2020, 1, 1)
    for i in range(_N):
        candidate_id = f"DFE-E2E-{i:04d}"
        # One distinct calendar date per candidate -- matches the real
        # production 540's own verified invariant (TARGET_PROMOTION_
        # CONFLICTS=0 -- zero internal (asset, date) duplicates), unlike
        # a modulo-based generator which would alias multiple candidates
        # onto the same date for the same asset.
        occurrence_date = (base_date + timedelta(days=i)).isoformat()
        fields = json.dumps({
            "asset_type": "PUMP", "occurrence_date": occurrence_date,
            "candidate_identity_v2": f"HASH-{i:04d}",
        })
        rows.append(
            f"('{candidate_id}', 'PDF-E2E', 'PDF', 'HISTORICAL_PM_OCCURRENCE_CANDIDATE', "
            f"'deterministic_workbook_table_parser', '{fields}'::jsonb, 'PENDING_REVIEW', '{_ASSET_CODE}')"
        )
    r.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status, pump_tag_number) VALUES "
        + ", ".join(rows) + ";"
    )
    return r


@pytest.fixture
def candidate_ids():
    return [f"DFE-E2E-{i:04d}" for i in range(_N)]


def test_540_pending_to_reviewed_to_promoted_then_idempotent_rerun(runner, candidate_ids):
    staging_repo = HistoricalPMCMONStagingRepository(runner)
    pm_repo = PMOccurrenceRepository(runner)

    pre_pm_rows = int(runner.query_scalar("SELECT count(*) FROM pm_occurrence") or "0")
    assert pre_pm_rows == 0

    # exact bulk review -- 540 PENDING_REVIEW -> 540 REVIEWED
    review_result = bulk_review_candidates(staging_repo, candidate_ids, reviewed_by=_ACTOR)
    assert review_result["status"] == "REVIEWED"
    assert len(review_result["reviewed"]) == _N
    reviewed_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM document_field_extraction WHERE status = 'REVIEWED' "
            f"AND document_field_extraction_id LIKE 'DFE-E2E-%'"
        )
        or "0"
    )
    assert reviewed_count == _N

    # exact atomic batch promotion -- 540 REVIEWED -> 540 SAVED + 540 pm_occurrence
    promote_result = promote_pm_batch(
        staging_repo, pm_repo, candidate_ids,
        pm_schedule_code="UNSCHEDULED::HOC-E2E-2026", promoted_by=_ACTOR,
    )
    assert promote_result["status"] == "PROMOTED"

    post_pm_rows = int(runner.query_scalar("SELECT count(*) FROM pm_occurrence") or "0")
    saved_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM document_field_extraction WHERE status = 'SAVED' "
            "AND document_field_extraction_id LIKE 'DFE-E2E-%'"
        )
        or "0"
    )
    pm_delta = post_pm_rows - pre_pm_rows
    assert pm_delta == _N
    assert saved_count == _N

    # exact retry of the SAME 540-id request -- must be a safe no-op.
    rerun_result = promote_pm_batch(
        staging_repo, pm_repo, candidate_ids,
        pm_schedule_code="UNSCHEDULED::HOC-E2E-2026", promoted_by=_ACTOR,
    )
    assert rerun_result["status"] == "PROMOTED"  # all ALREADY_PROMOTED -> still a valid, successful no-op batch
    final_pm_rows = int(runner.query_scalar("SELECT count(*) FROM pm_occurrence") or "0")
    pm_delta_on_rerun = final_pm_rows - post_pm_rows
    assert pm_delta_on_rerun == 0

    distinct_source_refs = int(
        runner.query_scalar(
            "SELECT count(DISTINCT source_reference) FROM pm_occurrence WHERE source_reference LIKE 'document_field_extraction:DFE-E2E-%'"
        )
        or "0"
    )
    assert distinct_source_refs == _N
