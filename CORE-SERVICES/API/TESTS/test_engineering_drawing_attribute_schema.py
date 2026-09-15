"""MWO-LTSA-DRAWING-INPUT-R5A -- proves migration 039 (knowledge_source_
registry.object_storage_key, document_field_extraction's new
ENGINEERING_DRAWING_CANDIDATE detected_document_type value,
engineering_drawing_attribute) against a REAL, disposable, published-port
Postgres. Same container/bootstrap/truncate pattern as
test_engineering_drawing_schema.py (Drawing-R3).
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

_CONTAINER_NAME = "ai5r-test-engineering-drawing-attribute-pg"
_USER = "ai5r"
_PASSWORD = "test-engineering-drawing-attribute-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATION_039 = _DATABASE_DIR / "MIGRATIONS" / "039_create_engineering_drawing_attribute.sql"
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
        "TRUNCATE engineering_drawing_attribute, engineering_drawing_bom_line, engineering_drawing_link, "
        "engineering_drawing_revision_artifact, engineering_drawing_revision, engineering_drawing, "
        "document_field_extraction, knowledge_source_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES "
        "('KS-1', 'DRAWING', 'Source 1'), ('KS-2', 'DRAWING', 'Source 2');"
    )
    r.execute_script(
        "INSERT INTO engineering_drawing (drawing_code, title) VALUES ('D1', 'Test Drawing');"
    )
    r.execute_script(
        "INSERT INTO engineering_drawing_revision (revision_code, drawing_code) VALUES "
        "('R1', 'D1'), ('R2', 'D1');"
    )
    r.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id) VALUES "
        "('A1', 'R1', 'KS-1'), ('A2', 'R2', 'KS-2');"
    )
    return r


def _rows(runner, sql):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


def _insert_attribute(
    runner, code="ATTR-1", revision_code="R1", source_artifact_code=None, attribute_concept="SEAL_TYPE",
    value_numeric=None, value_text="'8B1RS'", unit=None, source_location=None,
    verification_status="DRAFT", reviewed_by=None, reviewed_at=None,
):
    artifact_sql = "NULL" if source_artifact_code is None else f"'{source_artifact_code}'"
    numeric_sql = "NULL" if value_numeric is None else str(value_numeric)
    text_sql = "NULL" if value_text is None else (value_text if value_text.startswith("'") else f"'{value_text}'")
    unit_sql = "NULL" if unit is None else f"'{unit}'"
    location_sql = "NULL" if source_location is None else f"'{source_location}'"
    reviewed_by_sql = "NULL" if reviewed_by is None else f"'{reviewed_by}'"
    reviewed_at_sql = "NULL" if reviewed_at is None else f"'{reviewed_at}'"
    runner.execute_script(
        "INSERT INTO engineering_drawing_attribute "
        "(attribute_code, revision_code, source_artifact_code, attribute_concept, value_numeric, value_text, "
        "unit, source_location, verification_status, reviewed_by, reviewed_at) VALUES "
        f"('{code}', '{revision_code}', {artifact_sql}, '{attribute_concept}', {numeric_sql}, {text_sql}, "
        f"{unit_sql}, {location_sql}, '{verification_status}', {reviewed_by_sql}, {reviewed_at_sql});"
    )
    return code


# ---- knowledge_source_registry.object_storage_key ----

def test_object_storage_key_column_exists_and_nullable(runner):
    row = _rows(runner, "SELECT object_storage_key FROM knowledge_source_registry WHERE knowledge_source_id = 'KS-1'")[0]
    assert row["object_storage_key"] is None


def test_duplicate_object_storage_key_allowed(runner):
    key = "abcd1234.../pdf"
    runner.execute_script(f"UPDATE knowledge_source_registry SET object_storage_key = '{key}' WHERE knowledge_source_id = 'KS-1';")
    runner.execute_script(f"UPDATE knowledge_source_registry SET object_storage_key = '{key}' WHERE knowledge_source_id = 'KS-2';")
    assert _count(runner, f"SELECT COUNT(*) FROM knowledge_source_registry WHERE object_storage_key = '{key}'") == 2


def test_existing_knowledge_source_row_preserved(runner):
    row = _rows(runner, "SELECT source_type, source_name FROM knowledge_source_registry WHERE knowledge_source_id = 'KS-1'")[0]
    assert row["source_type"] == "DRAWING"
    assert row["source_name"] == "Source 1"


# ---- document_field_extraction.detected_document_type ----

def _insert_dfe(runner, code, detected_type):
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type) VALUES "
        f"('{code}', 'SRC-1', 'PDF', '{detected_type}');"
    )


def test_engineering_drawing_candidate_accepted(runner):
    _insert_dfe(runner, "DFE-1", "ENGINEERING_DRAWING_CANDIDATE")
    row = _rows(runner, "SELECT detected_document_type FROM document_field_extraction WHERE document_field_extraction_id = 'DFE-1'")[0]
    assert row["detected_document_type"] == "ENGINEERING_DRAWING_CANDIDATE"


@pytest.mark.parametrize("detected_type", [
    "MECHANICAL_SEAL_INSTALLATION_REPORT", "PUMP_DATASHEET", "MECHANICAL_SEAL_DRAWING",
    "PUMP_DRAWING", "NAMEPLATE", "UNKNOWN", "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
    "HISTORICAL_CMON_READING_CANDIDATE", "HISTORICAL_FINDING_CANDIDATE",
])
def test_existing_detected_document_types_still_accepted(runner, detected_type):
    _insert_dfe(runner, "DFE-1", detected_type)
    row = _rows(runner, "SELECT detected_document_type FROM document_field_extraction WHERE document_field_extraction_id = 'DFE-1'")[0]
    assert row["detected_document_type"] == detected_type


def test_invalid_detected_document_type_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_dfe(runner, "DFE-1", "BOGUS_TYPE")


# ---- engineering_drawing_attribute table ----

def test_attribute_table_created(runner):
    rows = _rows(
        runner,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
        "AND table_name = 'engineering_drawing_attribute'",
    )
    assert len(rows) == 1


def test_numeric_only_attribute(runner):
    _insert_attribute(runner, attribute_concept="SHAFT_DIAMETER", value_numeric=45.5, value_text=None, unit="mm")
    row = _rows(runner, "SELECT value_numeric, value_text, unit FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert float(row["value_numeric"]) == 45.5
    assert row["value_text"] is None
    assert row["unit"] == "mm"


def test_text_only_attribute(runner):
    _insert_attribute(runner, attribute_concept="FACE_MATERIAL", value_numeric=None, value_text="'Silicon Carbide'")
    row = _rows(runner, "SELECT value_numeric, value_text FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["value_numeric"] is None
    assert row["value_text"] == "Silicon Carbide"


def test_numeric_and_text_attribute(runner):
    _insert_attribute(runner, attribute_concept="PORT_SIZE", value_numeric=0.5, value_text="'1/2 NPT'", unit="inch")
    row = _rows(runner, "SELECT value_numeric, value_text FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert float(row["value_numeric"]) == 0.5
    assert row["value_text"] == "1/2 NPT"


def test_both_null_value_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_attribute(runner, value_numeric=None, value_text=None)


def test_open_attribute_concept_accepted(runner):
    _insert_attribute(runner, attribute_concept="SOME_FUTURE_CONCEPT_NOT_YET_LISTED", value_text="'x'")
    row = _rows(runner, "SELECT attribute_concept FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["attribute_concept"] == "SOME_FUTURE_CONCEPT_NOT_YET_LISTED"


def test_unit_nullable_and_source_text_preserved(runner):
    _insert_attribute(runner, value_text="'8B1RS'", unit=None)
    row = _rows(runner, "SELECT unit, value_text FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["unit"] is None
    assert row["value_text"] == "8B1RS"


def test_source_location_preserved(runner):
    _insert_attribute(runner, value_text="'x'", source_location="Detail A, page 2")
    row = _rows(runner, "SELECT source_location FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["source_location"] == "Detail A, page 2"


# ---- verification status / review metadata ----

def test_draft_without_reviewer_accepted(runner):
    _insert_attribute(runner, verification_status="DRAFT", value_text="'x'")
    row = _rows(runner, "SELECT verification_status, reviewed_by FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["verification_status"] == "DRAFT"
    assert row["reviewed_by"] is None


def test_under_review_without_reviewer_accepted(runner):
    _insert_attribute(runner, verification_status="UNDER_REVIEW", value_text="'x'")
    row = _rows(runner, "SELECT verification_status FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["verification_status"] == "UNDER_REVIEW"


def test_verified_requires_reviewer_metadata(runner):
    with pytest.raises(psycopg2.Error):
        _insert_attribute(runner, verification_status="VERIFIED", value_text="'x'")


def test_verified_with_reviewer_metadata_accepted(runner):
    _insert_attribute(
        runner, verification_status="VERIFIED", value_text="'x'",
        reviewed_by=_ACTOR, reviewed_at="2026-06-15 00:00:00",
    )
    row = _rows(runner, "SELECT verification_status, reviewed_by FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["verification_status"] == "VERIFIED"
    assert row["reviewed_by"] == _ACTOR


def test_canonical_requires_reviewer_metadata(runner):
    with pytest.raises(psycopg2.Error):
        _insert_attribute(runner, verification_status="CANONICAL", value_text="'x'")


def test_canonical_with_reviewer_metadata_accepted(runner):
    _insert_attribute(
        runner, verification_status="CANONICAL", value_text="'x'",
        reviewed_by=_ACTOR, reviewed_at="2026-06-15 00:00:00",
    )
    row = _rows(runner, "SELECT verification_status FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["verification_status"] == "CANONICAL"


# ---- source artifact integrity ----

def test_valid_source_artifact_same_revision(runner):
    _insert_attribute(runner, revision_code="R1", source_artifact_code="A1", value_text="'x'")
    row = _rows(runner, "SELECT source_artifact_code FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["source_artifact_code"] == "A1"


def test_cross_revision_source_artifact_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_attribute(runner, revision_code="R1", source_artifact_code="A2", value_text="'x'")


def test_missing_source_artifact_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_attribute(runner, revision_code="R1", source_artifact_code="NO-SUCH-ARTIFACT", value_text="'x'")


def test_null_source_artifact_always_accepted(runner):
    _insert_attribute(runner, revision_code="R1", source_artifact_code=None, value_text="'x'")
    row = _rows(runner, "SELECT source_artifact_code FROM engineering_drawing_attribute WHERE attribute_code = 'ATTR-1'")[0]
    assert row["source_artifact_code"] is None


# ---- multiple attributes / delete policy ----

def test_multiple_same_concept_attributes_per_revision_allowed(runner):
    _insert_attribute(runner, code="ATTR-1", attribute_concept="PORT_SIZE", value_text="'port 1'")
    _insert_attribute(runner, code="ATTR-2", attribute_concept="PORT_SIZE", value_text="'port 2'")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute WHERE revision_code = 'R1' AND attribute_concept = 'PORT_SIZE'") == 2


def test_revision_deletion_restricted_by_attribute(runner):
    _insert_attribute(runner, revision_code="R1", value_text="'x'")
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM engineering_drawing_revision WHERE revision_code = 'R1';")


def test_artifact_deletion_restricted_by_attribute(runner):
    _insert_attribute(runner, revision_code="R1", source_artifact_code="A1", value_text="'x'")
    with pytest.raises(psycopg2.Error):
        runner.execute_script("DELETE FROM engineering_drawing_revision_artifact WHERE artifact_code = 'A1';")


# ---- no existing data mutation / migration re-apply ----

def test_existing_drawing_r3_rows_unchanged(runner):
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 1
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision") == 2
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact") == 2


def test_migration_reapply_is_safe(runner):
    before = (
        _count(runner, "SELECT COUNT(*) FROM knowledge_source_registry"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact"),
    )
    migration_sql = _MIGRATION_039.read_text(encoding="utf-8")
    runner.execute_script(migration_sql)
    after = (
        _count(runner, "SELECT COUNT(*) FROM knowledge_source_registry"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision"),
        _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact"),
    )
    assert before == after
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 0


def test_zero_attribute_rows_after_fresh_migration(runner):
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 0
