"""MWO-LTSA-DRAWING-INPUT-R5D.0A -- proves migration 040
(engineering_drawing_promotion) against a REAL, disposable, published-port
Postgres. Same container/bootstrap/truncate pattern as
test_engineering_drawing_attribute_schema.py (Drawing-R5A).

SCOPE NOTE: this file intentionally does NOT test drawing/revision
identity-uniqueness (upper(btrim(manufacturer))/drawing_number,
drawing_code/revision) -- those two expression/partial unique indexes were
NOT created by migration 040 (deferred pending a live duplicate-data audit
this mission could not complete; see migration 040's own header comment
and the R5D.0A FINAL OUTPUT's DRAWING_IDENTITY_DUPLICATES/
REVISION_IDENTITY_DUPLICATES fields). Only the promotion table itself is
covered here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402

_CONTAINER_NAME = "ai5r-test-engineering-drawing-promotion-pg"
_USER = "ai5r"
_PASSWORD = "test-engineering-drawing-promotion-password"
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
        "035_retarget_document_field_extraction_to_asset_registry.sql",
        "036_create_ltsa_contract_scope.sql",
        "037_create_ltsa_finding_and_cm_measurement.sql",
        "038_create_engineering_drawing.sql",
        "039_create_engineering_drawing_attribute.sql",
        "040_create_engineering_drawing_promotion.sql",
    )
]

_ACTOR = "00000000-0000-0000-0000-000000000001"


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
        "TRUNCATE engineering_drawing_promotion, engineering_drawing_attribute, engineering_drawing_bom_line, "
        "engineering_drawing_link, engineering_drawing_revision_artifact, engineering_drawing_revision, "
        "engineering_drawing, document_field_extraction, knowledge_source_registry RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES "
        "('KS-1', 'DRAWING', 'Source 1');"
    )
    r.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, status) "
        "VALUES ('DFE-1', 'KS-1', 'PDF', 'ENGINEERING_DRAWING_CANDIDATE', 'REVIEWED'), "
        "('DFE-2', 'KS-1', 'PDF', 'ENGINEERING_DRAWING_CANDIDATE', 'REVIEWED');"
    )
    r.execute_script("INSERT INTO engineering_drawing (drawing_code, title) VALUES ('D1', 'Test Drawing'), ('D2', 'Other Drawing');")
    r.execute_script(
        "INSERT INTO engineering_drawing_revision (revision_code, drawing_code) VALUES ('R1', 'D1'), ('R2', 'D2');"
    )
    r.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id) VALUES "
        "('A1', 'R1', 'KS-1'), ('A2', 'R2', 'KS-1');"
    )
    return r


def _rows(runner, sql):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


def _insert_promotion(
    runner, promotion_code="PROMO-1", candidate_id="DFE-1", drawing_code="D1",
    revision_code="R1", artifact_code="A1", promoted_by=_ACTOR, promoted_at="2026-09-15 12:00:00",
):
    runner.execute_script(
        "INSERT INTO engineering_drawing_promotion "
        "(promotion_code, candidate_id, drawing_code, revision_code, artifact_code, promoted_by, promoted_at) VALUES "
        f"('{promotion_code}', '{candidate_id}', '{drawing_code}', '{revision_code}', '{artifact_code}', "
        f"'{promoted_by}', '{promoted_at}');"
    )
    return promotion_code


# ---- table existence / basic insert ----

def test_promotion_table_exists_and_accepts_valid_row(runner):
    _insert_promotion(runner)
    row = _rows(runner, "SELECT * FROM engineering_drawing_promotion WHERE promotion_code = 'PROMO-1'")[0]
    assert row["candidate_id"] == "DFE-1"
    assert row["drawing_code"] == "D1"
    assert row["revision_code"] == "R1"
    assert row["artifact_code"] == "A1"


# ---- UNIQUE(candidate_id) ----

def test_unique_candidate_id_enforced(runner):
    _insert_promotion(runner, promotion_code="PROMO-1", candidate_id="DFE-1")
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, promotion_code="PROMO-2", candidate_id="DFE-1")


def test_two_distinct_candidates_each_get_own_promotion(runner):
    _insert_promotion(runner, promotion_code="PROMO-1", candidate_id="DFE-1", drawing_code="D1", revision_code="R1", artifact_code="A1")
    _insert_promotion(runner, promotion_code="PROMO-2", candidate_id="DFE-2", drawing_code="D2", revision_code="R2", artifact_code="A2")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_promotion") == 2


# ---- FK RESTRICT: candidate ----

def test_candidate_fk_rejects_unknown_candidate(runner):
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, candidate_id="DFE-MISSING")


def test_candidate_row_cannot_be_deleted_once_promoted(runner):
    _insert_promotion(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM document_field_extraction WHERE document_field_extraction_id = 'DFE-1';")


# ---- FK RESTRICT: drawing ----

def test_drawing_fk_rejects_unknown_drawing(runner):
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, drawing_code="D-MISSING")


def test_drawing_row_cannot_be_deleted_once_promoted(runner):
    _insert_promotion(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM engineering_drawing WHERE drawing_code = 'D1';")


# ---- revision/artifact composite-FK consistency ----

def test_revision_must_belong_to_same_drawing(runner):
    # R2 belongs to D2, not D1 -- the composite FK must reject this combination.
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, drawing_code="D1", revision_code="R2", artifact_code="A1")


def test_artifact_must_belong_to_same_revision(runner):
    # A2 belongs to R2, not R1 -- the composite FK must reject this combination.
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, drawing_code="D1", revision_code="R1", artifact_code="A2")


def test_revision_fk_rejects_unknown_revision(runner):
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, revision_code="R-MISSING")


def test_artifact_fk_rejects_unknown_artifact(runner):
    with pytest.raises(psycopg2.Error):
        _insert_promotion(runner, artifact_code="A-MISSING")


def test_revision_row_cannot_be_deleted_once_promoted(runner):
    _insert_promotion(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM engineering_drawing_revision WHERE revision_code = 'R1';")


def test_artifact_row_cannot_be_deleted_once_promoted(runner):
    _insert_promotion(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM engineering_drawing_revision_artifact WHERE artifact_code = 'A1';")


# ---- no existing Drawing data changed by this migration ----

def test_no_existing_drawing_rows_mutated(runner):
    row = _rows(runner, "SELECT title FROM engineering_drawing WHERE drawing_code = 'D1'")[0]
    assert row["title"] == "Test Drawing"
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 2


def test_promotion_table_starts_empty(runner):
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_promotion") == 0


# ---- R5D.0A1: drawing identity uniqueness (trim + case-insensitive manufacturer, exact drawing_number) ----

def _insert_drawing(runner, drawing_code, manufacturer=None, drawing_number=None, title="T"):
    manufacturer_sql = "NULL" if manufacturer is None else f"'{manufacturer}'"
    drawing_number_sql = "NULL" if drawing_number is None else f"'{drawing_number}'"
    runner.execute_script(
        "INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number) VALUES "
        f"('{drawing_code}', '{title}', {manufacturer_sql}, {drawing_number_sql});"
    )


def test_manufacturer_case_variant_same_drawing_number_rejected(runner):
    _insert_drawing(runner, "ID-1", manufacturer="John Crane", drawing_number="DWG-100")
    with pytest.raises(psycopg2.Error):
        _insert_drawing(runner, "ID-2", manufacturer="JOHN CRANE", drawing_number="DWG-100")


def test_manufacturer_padded_whitespace_variant_rejected(runner):
    _insert_drawing(runner, "ID-1", manufacturer=" John Crane ", drawing_number="DWG-100")
    with pytest.raises(psycopg2.Error):
        _insert_drawing(runner, "ID-2", manufacturer="JOHN CRANE", drawing_number="DWG-100")


def test_manufacturer_without_space_remains_distinct(runner):
    _insert_drawing(runner, "ID-1", manufacturer="JOHNCRANE", drawing_number="DWG-100")
    _insert_drawing(runner, "ID-2", manufacturer="JOHN CRANE", drawing_number="DWG-100")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_code IN ('ID-1', 'ID-2')") == 2


def test_different_drawing_number_allowed(runner):
    _insert_drawing(runner, "ID-1", manufacturer="John Crane", drawing_number="DWG-100")
    _insert_drawing(runner, "ID-2", manufacturer="JOHN CRANE", drawing_number="DWG-200")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_code IN ('ID-1', 'ID-2')") == 2


def test_null_drawing_number_allowed_multiple(runner):
    _insert_drawing(runner, "ID-1", manufacturer="John Crane", drawing_number=None)
    _insert_drawing(runner, "ID-2", manufacturer="John Crane", drawing_number=None)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_code IN ('ID-1', 'ID-2')") == 2


def test_null_manufacturer_allowed_multiple_same_drawing_number(runner):
    _insert_drawing(runner, "ID-1", manufacturer=None, drawing_number="DWG-100")
    _insert_drawing(runner, "ID-2", manufacturer=None, drawing_number="DWG-100")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_code IN ('ID-1', 'ID-2')") == 2


# ---- R5D.0A1: revision identity uniqueness (exact drawing_code + revision, NULL repeatable) ----

def _insert_revision_row(runner, revision_code, drawing_code, revision=None):
    revision_sql = "NULL" if revision is None else f"'{revision}'"
    runner.execute_script(
        f"INSERT INTO engineering_drawing_revision (revision_code, drawing_code, revision) VALUES "
        f"('{revision_code}', '{drawing_code}', {revision_sql});"
    )


def test_same_drawing_same_revision_rejected(runner):
    _insert_revision_row(runner, "RV-1", "D1", revision="B")
    with pytest.raises(psycopg2.Error):
        _insert_revision_row(runner, "RV-2", "D1", revision="B")


def test_different_drawing_same_revision_allowed(runner):
    _insert_revision_row(runner, "RV-1", "D1", revision="B")
    _insert_revision_row(runner, "RV-2", "D2", revision="B")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision WHERE revision_code IN ('RV-1', 'RV-2')") == 2


def test_same_drawing_multiple_null_revisions_allowed(runner):
    _insert_revision_row(runner, "RV-1", "D1", revision=None)
    _insert_revision_row(runner, "RV-2", "D1", revision=None)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision WHERE revision_code IN ('RV-1', 'RV-2')") == 2
