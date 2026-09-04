"""MWO-LTSA-HISTORICAL-PM-FINALIZATION-001 -- real-Postgres proof for
PMOccurrenceRepository.finalize_historical_batch_atomic() and the
historical_pm_finalization_service module above it: a genuine, disposable
Postgres container (same discipline as test_historical_pm_promotion_e2e_
real_db.py / test_pm_occurrence_repository_real_db.py), never a Fake, so
the atomic SQL's own precheck/postcheck DO blocks, the audit INSERT, and
the WHERE workflow_status = 'DRAFT' guard are all exercised for real.
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
from API.historical_pm_finalization_service import (  # noqa: E402
    fetch_finalization_targets,
    finalization_readiness,
    finalize_historical_pm_batch,
    validate_finalization_batch,
)

_CONTAINER_NAME = "ai5r-test-pm-finalization-e2e-pg"
_USER = "ai5r"
_PASSWORD = "test-pm-finalization-e2e-password"
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
_FINALIZER = "33333333-3333-3333-3333-333333333333"
_N = 5


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
    return r


@pytest.fixture
def candidate_ids():
    return [f"DFE-FIN-{i:04d}" for i in range(_N)]


def _stage_review_promote(runner, candidate_ids):
    """Common setup: N PENDING_REVIEW candidates -> REVIEWED -> promoted
    (SAVED + real DRAFT pm_occurrence rows), exactly the state production
    was in before this MWO. Returns (staging_repo, pm_repo)."""
    staging_repo = HistoricalPMCMONStagingRepository(runner)
    pm_repo = PMOccurrenceRepository(runner)

    base_date = date(2020, 1, 1)
    rows = []
    for i, candidate_id in enumerate(candidate_ids):
        occurrence_date = (base_date + timedelta(days=i)).isoformat()
        fields = json.dumps({
            "asset_type": "PUMP", "occurrence_date": occurrence_date,
            "candidate_identity_v2": f"HASH-{i:04d}",
        })
        rows.append(
            f"('{candidate_id}', 'PDF-FIN-E2E', 'PDF', 'HISTORICAL_PM_OCCURRENCE_CANDIDATE', "
            f"'deterministic_workbook_table_parser', '{fields}'::jsonb, 'PENDING_REVIEW', '{_ASSET_CODE}')"
        )
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status, pump_tag_number) VALUES "
        + ", ".join(rows) + ";"
    )

    bulk_review_candidates(staging_repo, candidate_ids, reviewed_by=_ACTOR)
    promote_result = promote_pm_batch(
        staging_repo, pm_repo, candidate_ids,
        pm_schedule_code="UNSCHEDULED::HOC-FIN-E2E-2026", promoted_by=_ACTOR,
    )
    assert promote_result["status"] == "PROMOTED"
    return staging_repo, pm_repo


def test_full_finalization_moves_draft_to_finalized_with_audit(runner, candidate_ids):
    staging_repo, pm_repo = _stage_review_promote(runner, candidate_ids)

    pre_draft_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM pm_occurrence WHERE workflow_status = 'DRAFT' AND deleted_at IS NULL"
        ) or "0"
    )
    assert pre_draft_count == _N

    result = finalize_historical_pm_batch(staging_repo, pm_repo, finalized_by=_FINALIZER)
    assert result["status"] == "FINALIZED"
    assert result["finalized_count"] == _N

    finalized_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM pm_occurrence WHERE workflow_status = 'FINALIZED' AND deleted_at IS NULL"
        ) or "0"
    )
    assert finalized_count == _N

    # 18: normal PM workflow columns untouched by this bypass -- no
    # submitted_by/reviewed_by/technical_reviewed_by ever gets fabricated.
    unexpected_workflow_fields = int(
        runner.query_scalar(
            "SELECT count(*) FROM pm_occurrence WHERE workflow_status = 'FINALIZED' "
            "AND (submitted_by IS NOT NULL OR reviewed_by IS NOT NULL OR technical_reviewed_by IS NOT NULL)"
        ) or "0"
    )
    assert unexpected_workflow_fields == 0

    # Do NOT change: occurrence_date/pump/source_reference/schedule code/
    # legacy status/PM content -- only workflow_status/updated_by/
    # updated_at differ from the pre-finalize DRAFT snapshot.
    unchanged_check = int(
        runner.query_scalar(
            "SELECT count(*) FROM pm_occurrence WHERE workflow_status = 'FINALIZED' "
            "AND asset_code = '211-P-13AR' AND status = 'DONE' "
            "AND pm_schedule_code = 'UNSCHEDULED::HOC-FIN-E2E-2026' "
            "AND source_reference LIKE 'document_field_extraction:DFE-FIN-%'"
        ) or "0"
    )
    assert unchanged_check == _N

    # 16: exactly one HISTORICAL_FINALIZE_BATCH audit row per finalized PM.
    audit_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE entity_type = 'PM_OCCURRENCE' "
            "AND reason = 'HISTORICAL_FINALIZE_BATCH'"
        ) or "0"
    )
    assert audit_count == _N

    # Audit content: explicit DRAFT -> FINALIZED, source_reference
    # preserved, actor is the authenticated finalizer, never spoofed.
    sample = json.loads(runner.query_scalar(
        "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
        "SELECT old_value, new_value, changed_by, source_reference FROM record_change_history "
        "WHERE entity_type = 'PM_OCCURRENCE' AND reason = 'HISTORICAL_FINALIZE_BATCH' LIMIT 1"
        ") t"
    ) or "[]")[0]
    assert sample["old_value"] == "DRAFT"
    assert sample["new_value"] == "FINALIZED"
    assert sample["changed_by"] == _FINALIZER
    assert sample["source_reference"].startswith("document_field_extraction:DFE-FIN-")

    # Staging candidate status untouched by finalization (still SAVED,
    # exactly as promotion left it).
    saved_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM document_field_extraction WHERE status = 'SAVED' "
            "AND document_field_extraction_id LIKE 'DFE-FIN-%'"
        ) or "0"
    )
    assert saved_count == _N


def test_17_retry_after_full_success_is_zero_mutation_zero_new_audit(runner, candidate_ids):
    staging_repo, pm_repo = _stage_review_promote(runner, candidate_ids)
    first = finalize_historical_pm_batch(staging_repo, pm_repo, finalized_by=_FINALIZER)
    assert first["finalized_count"] == _N

    audit_count_after_first = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE reason = 'HISTORICAL_FINALIZE_BATCH'"
        ) or "0"
    )
    assert audit_count_after_first == _N

    second = finalize_historical_pm_batch(staging_repo, pm_repo, finalized_by=_FINALIZER)
    assert second["status"] == "FINALIZED"
    assert second["finalized_count"] == 0  # zero additional mutation

    audit_count_after_second = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE reason = 'HISTORICAL_FINALIZE_BATCH'"
        ) or "0"
    )
    assert audit_count_after_second == audit_count_after_first  # no duplicate audit rows

    readiness = finalization_readiness(staging_repo, pm_repo)
    assert readiness == {
        "target_count": _N, "draft_count": 0, "finalized_count": _N,
        "invalid_count": 0, "finalization_ready": False,
    }


def test_13_atomic_rollback_on_one_invalid_member(runner, candidate_ids):
    staging_repo, pm_repo = _stage_review_promote(runner, candidate_ids)

    # Corrupt exactly ONE of the N eligible pm_occurrence rows so it is
    # no longer DRAFT (simulating a stale/racing precheck) -- the atomic
    # method's own re-derived eligibility check must reject the WHOLE
    # batch, writing nothing, not just skip the one bad row.
    target_row = json.loads(runner.query_scalar(
        f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
        f"SELECT pm_occurrence_code FROM pm_occurrence WHERE source_reference = "
        f"'document_field_extraction:{candidate_ids[0]}' LIMIT 1) t"
    ) or "[]")[0]
    runner.execute_script(
        f"UPDATE pm_occurrence SET workflow_status = 'SUBMITTED' "
        f"WHERE pm_occurrence_code = '{target_row['pm_occurrence_code']}';"
    )

    all_codes = json.loads(runner.query_scalar(
        "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM "
        "(SELECT pm_occurrence_code FROM pm_occurrence WHERE deleted_at IS NULL) t"
    ) or "[]")
    codes = [r["pm_occurrence_code"] for r in all_codes]
    assert len(codes) == _N

    with pytest.raises(Exception):  # noqa: B017 -- DB driver exception type varies
        pm_repo.finalize_historical_batch_atomic(codes, finalized_by=_FINALIZER)

    # Nothing committed: every row (including the still-genuinely-
    # eligible ones) remains exactly as it was before the attempt.
    finalized_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM pm_occurrence WHERE workflow_status = 'FINALIZED'"
        ) or "0"
    )
    assert finalized_count == 0
    audit_count = int(
        runner.query_scalar(
            "SELECT count(*) FROM record_change_history WHERE reason = 'HISTORICAL_FINALIZE_BATCH'"
        ) or "0"
    )
    assert audit_count == 0


def test_18_normal_digital_pm_draft_submit_finalize_workflow_unaffected(runner):
    # A completely ordinary, non-historical PM draft (no source_
    # reference) -- never touched by fetch_finalization_targets/
    # validate_finalization_batch (it is never a target at all), and its
    # own real DRAFT -> SUBMITTED -> FINALIZED path (pm_cm_workflow_
    # service.py, technical_finalize()) is exercised end to end,
    # completely independent of this MWO's new code path.
    pm_repo = PMOccurrenceRepository(runner)
    draft = pm_repo.create_draft(
        pm_schedule_code="UNSCHEDULED::MANUAL-E2E", asset_code=_ASSET_CODE, asset_type="PUMP",
        occurrence_date="2026-08-01", activities=None, remarks=None, created_by=_ACTOR,
    )
    assert draft["workflow_status"] == "DRAFT"
    assert draft["source_reference"] is None

    submitted = pm_repo.submit(draft["pm_occurrence_code"], submitted_by=_ACTOR)
    assert submitted["workflow_status"] == "SUBMITTED"

    finalized = pm_repo.technical_finalize(
        draft["pm_occurrence_code"], technical_reviewed_by=_ACTOR,
        technical_outcome="PASS", technical_comment=None, technical_recommendation=None,
    )
    assert finalized["workflow_status"] == "FINALIZED"

    # This ordinary PM must never appear as a finalization target (it
    # has no matching recovery candidate) -- confirms the historical
    # bypass path never reaches an ordinary digital PM record.
    staging_repo = HistoricalPMCMONStagingRepository(runner)
    assert fetch_finalization_targets(staging_repo) == []
    validate_result = validate_finalization_batch(staging_repo, pm_repo)
    assert validate_result == {"results": [], "counts": {}, "all_eligible": True, "eligible_pm_occurrence_codes": []}
