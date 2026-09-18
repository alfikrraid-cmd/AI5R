"""MWO-LTSA-DRAWING-INPUT-R3 -- proves migration 038 (engineering_drawing,
engineering_drawing_revision, engineering_drawing_revision_artifact,
engineering_drawing_link, engineering_drawing_bom_line) against a REAL,
disposable, published-port Postgres. Same container/bootstrap/truncate
pattern as test_ltsa_finding_and_cm_measurement_schema.py (R3 Reporting).
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

_CONTAINER_NAME = "ai5r-test-engineering-drawing-pg"
_USER = "ai5r"
_PASSWORD = "test-engineering-drawing-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATION_038 = _DATABASE_DIR / "MIGRATIONS" / "038_create_engineering_drawing.sql"
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
    )
]

_ASSET = "211-P-13AR"
_SEAL = "SEAL-1"
_COMPONENT = "CMP-1"


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
        "TRUNCATE engineering_drawing_bom_line, engineering_drawing_link, "
        "engineering_drawing_revision_artifact, engineering_drawing_revision, engineering_drawing, "
        "knowledge_source_registry, internal_component_master, asset_registry, seal_registry, ltsa_pumps "
        "RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_ASSET}', '{_ASSET}', 'PUMP', 'HOC', 'Active');"
    )
    r.execute_script(
        f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL}', 'Test Seal');"
    )
    r.execute_script(
        "INSERT INTO internal_component_master (component_id, component_class, gpn_status, identity_fingerprint, description) "
        f"VALUES ('{_COMPONENT}', 'O_RING', 'GPN_PENDING', 'FP-1', 'Test O-Ring');"
    )
    r.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES "
        "('KS-1', 'DRAWING', 'Test Source 1'), ('KS-2', 'DRAWING', 'Test Source 2'), "
        "('KS-3', 'DRAWING', 'Test Source 3'), ('KS-4', 'DRAWING', 'Test Source 4');"
    )
    return r


def _rows(runner, sql):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


def _insert_drawing(runner, code="ENGDRW-1", drawing_number="DWG-100", title="Test Drawing"):
    number_sql = "NULL" if drawing_number is None else f"'{drawing_number}'"
    runner.execute_script(
        f"INSERT INTO engineering_drawing (drawing_code, drawing_number, title) VALUES "
        f"('{code}', {number_sql}, '{title}');"
    )
    return code


def _insert_revision(runner, code="ENGDRWREV-1", drawing_code="ENGDRW-1", revision="A"):
    revision_sql = "NULL" if revision is None else f"'{revision}'"
    runner.execute_script(
        f"INSERT INTO engineering_drawing_revision (revision_code, drawing_code, revision) VALUES "
        f"('{code}', '{drawing_code}', {revision_sql});"
    )
    return code


def _insert_artifact(runner, code="ENGART-1", revision_code="ENGDRWREV-1", knowledge_source_id="KS-1",
                      artifact_class="SOURCE_DOCUMENT"):
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class) "
        f"VALUES ('{code}', '{revision_code}', '{knowledge_source_id}', '{artifact_class}');"
    )
    return code


# ---- table existence ----

def test_all_five_tables_exist(runner):
    rows = _rows(
        runner,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN "
        "('engineering_drawing', 'engineering_drawing_revision', 'engineering_drawing_revision_artifact', "
        "'engineering_drawing_link', 'engineering_drawing_bom_line')",
    )
    names = {r["table_name"] for r in rows}
    assert names == {
        "engineering_drawing", "engineering_drawing_revision", "engineering_drawing_revision_artifact",
        "engineering_drawing_link", "engineering_drawing_bom_line",
    }


# ---- engineering_drawing ----

def test_drawing_number_nullable(runner):
    _insert_drawing(runner, code="D1", drawing_number=None)
    row = _rows(runner, "SELECT drawing_number FROM engineering_drawing WHERE drawing_code = 'D1'")[0]
    assert row["drawing_number"] is None


def test_drawing_number_not_unique(runner):
    _insert_drawing(runner, code="D1", drawing_number="DUP-1")
    _insert_drawing(runner, code="D2", drawing_number="DUP-1")  # must NOT raise
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_number = 'DUP-1'") == 2


def test_multiple_null_drawing_numbers_allowed(runner):
    _insert_drawing(runner, code="D1", drawing_number=None)
    _insert_drawing(runner, code="D2", drawing_number=None)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing WHERE drawing_number IS NULL") == 2


# ---- engineering_drawing_revision ----

def test_revision_nullable(runner):
    _insert_drawing(runner)
    _insert_revision(runner, revision=None)
    row = _rows(runner, "SELECT revision FROM engineering_drawing_revision WHERE revision_code = 'ENGDRWREV-1'")[0]
    assert row["revision"] is None


def test_multiple_null_revisions_per_drawing_allowed(runner):
    _insert_drawing(runner)
    _insert_revision(runner, code="R1", revision=None)
    _insert_revision(runner, code="R2", revision=None)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision WHERE drawing_code = 'ENGDRW-1'") == 2


def test_multiple_revisions_per_drawing(runner):
    _insert_drawing(runner)
    _insert_revision(runner, code="R1", revision="A")
    _insert_revision(runner, code="R2", revision="B")
    _insert_revision(runner, code="R3", revision="C")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision WHERE drawing_code = 'ENGDRW-1'") == 3


@pytest.mark.parametrize("status", ["DRAFT", "UNDER_REVIEW", "VERIFIED", "CANONICAL"])
def test_revision_verification_status_valid_values(runner, status):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, verification_status) VALUES "
        f"('R1', 'ENGDRW-1', '{status}');"
    )
    row = _rows(runner, "SELECT verification_status FROM engineering_drawing_revision WHERE revision_code = 'R1'")[0]
    assert row["verification_status"] == status


def test_revision_verification_status_invalid_rejected(runner):
    _insert_drawing(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, verification_status) VALUES "
            "('R1', 'ENGDRW-1', 'BOGUS');"
        )


def test_revision_no_self_supersede(runner):
    _insert_drawing(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, supersedes_revision_code) VALUES "
            "('R1', 'ENGDRW-1', 'R1');"
        )


def test_revision_supersedes_cross_drawing_rejected(runner):
    _insert_drawing(runner, code="D1")
    _insert_drawing(runner, code="D2")
    _insert_revision(runner, code="R1", drawing_code="D1")
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, supersedes_revision_code) VALUES "
            "('R2', 'D2', 'R1');"
        )


def test_revision_supersedes_same_drawing_accepted(runner):
    _insert_drawing(runner)
    _insert_revision(runner, code="R1")
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision (revision_code, drawing_code, supersedes_revision_code) VALUES "
        "('R2', 'ENGDRW-1', 'R1');"
    )
    row = _rows(runner, "SELECT supersedes_revision_code FROM engineering_drawing_revision WHERE revision_code = 'R2'")[0]
    assert row["supersedes_revision_code"] == "R1"


# ---- current_revision_code integrity ----

def test_current_revision_belongs_to_same_drawing_accepted(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "UPDATE engineering_drawing SET current_revision_code = 'ENGDRWREV-1' WHERE drawing_code = 'ENGDRW-1';"
    )
    row = _rows(runner, "SELECT current_revision_code FROM engineering_drawing WHERE drawing_code = 'ENGDRW-1'")[0]
    assert row["current_revision_code"] == "ENGDRWREV-1"


def test_cross_drawing_current_revision_rejected(runner):
    _insert_drawing(runner, code="D1")
    _insert_drawing(runner, code="D2")
    _insert_revision(runner, code="R1", drawing_code="D1")
    with pytest.raises(psycopg2.Error):
        runner.execute_script("UPDATE engineering_drawing SET current_revision_code = 'R1' WHERE drawing_code = 'D2';")


def test_current_revision_null_always_accepted(runner):
    _insert_drawing(runner)
    row = _rows(runner, "SELECT current_revision_code FROM engineering_drawing WHERE drawing_code = 'ENGDRW-1'")[0]
    assert row["current_revision_code"] is None


# ---- artifact ----

@pytest.mark.parametrize("artifact_class", ["SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET", "UNKNOWN"])
def test_artifact_class_valid_values(runner, artifact_class):
    _insert_drawing(runner)
    _insert_revision(runner)
    _insert_artifact(runner, artifact_class=artifact_class)
    row = _rows(runner, "SELECT artifact_class FROM engineering_drawing_revision_artifact WHERE artifact_code = 'ENGART-1'")[0]
    assert row["artifact_class"] == artifact_class


def test_artifact_class_invalid_rejected(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    with pytest.raises(psycopg2.Error):
        _insert_artifact(runner, artifact_class="BOGUS")


def test_artifact_class_default_unknown(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id) VALUES "
        "('ENGART-1', 'ENGDRWREV-1', 'KS-1');"
    )
    row = _rows(runner, "SELECT artifact_class FROM engineering_drawing_revision_artifact WHERE artifact_code = 'ENGART-1'")[0]
    assert row["artifact_class"] == "UNKNOWN"


def test_multiple_artifacts_per_revision(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    _insert_artifact(runner, code="A1", knowledge_source_id="KS-1")
    _insert_artifact(runner, code="A2", knowledge_source_id="KS-2")
    _insert_artifact(runner, code="A3", knowledge_source_id="KS-3")
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact WHERE revision_code = 'ENGDRWREV-1'") == 3


def test_all_four_artifact_classes_coexist_on_same_revision(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    _insert_artifact(runner, code="A1", knowledge_source_id="KS-1", artifact_class="SOURCE_DOCUMENT")
    _insert_artifact(runner, code="A2", knowledge_source_id="KS-2", artifact_class="SOURCE_CAD")
    _insert_artifact(runner, code="A3", knowledge_source_id="KS-3", artifact_class="DERIVED_CAD")
    _insert_artifact(runner, code="A4", knowledge_source_id="KS-4", artifact_class="VIEWER_ASSET")
    classes = {
        r["artifact_class"] for r in _rows(
            runner, "SELECT artifact_class FROM engineering_drawing_revision_artifact WHERE revision_code = 'ENGDRWREV-1'"
        )
    }
    assert classes == {"SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET"}


def test_one_primary_per_revision_and_artifact_class(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class, is_primary) VALUES "
        "('A1', 'ENGDRWREV-1', 'KS-1', 'DERIVED_CAD', TRUE);"
    )
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class, is_primary) VALUES "
            "('A2', 'ENGDRWREV-1', 'KS-2', 'DERIVED_CAD', TRUE);"
        )


def test_primary_allowed_independently_per_artifact_class(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class, is_primary) VALUES "
        "('A1', 'ENGDRWREV-1', 'KS-1', 'DERIVED_CAD', TRUE), "
        "('A2', 'ENGDRWREV-1', 'KS-2', 'VIEWER_ASSET', TRUE);"
    )
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact WHERE revision_code = 'ENGDRWREV-1' AND is_primary") == 2


def test_derived_artifact_lineage(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    _insert_artifact(runner, code="STEP-1", knowledge_source_id="KS-1", artifact_class="DERIVED_CAD")
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class, derived_from_artifact_code) VALUES "
        "('GLB-1', 'ENGDRWREV-1', 'KS-2', 'VIEWER_ASSET', 'STEP-1');"
    )
    row = _rows(runner, "SELECT derived_from_artifact_code FROM engineering_drawing_revision_artifact WHERE artifact_code = 'GLB-1'")[0]
    assert row["derived_from_artifact_code"] == "STEP-1"


def test_self_lineage_rejected(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, derived_from_artifact_code) VALUES "
            "('A1', 'ENGDRWREV-1', 'KS-1', 'A1');"
        )


def test_cross_revision_lineage_allowed(runner):
    _insert_drawing(runner)
    _insert_revision(runner, code="R1")
    _insert_revision(runner, code="R2")
    _insert_artifact(runner, code="STEP-OLD", revision_code="R1", knowledge_source_id="KS-1", artifact_class="DERIVED_CAD")
    runner.execute_script(
        "INSERT INTO engineering_drawing_revision_artifact (artifact_code, revision_code, knowledge_source_id, artifact_class, derived_from_artifact_code) VALUES "
        "('GLB-NEW', 'R2', 'KS-2', 'VIEWER_ASSET', 'STEP-OLD');"
    )
    row = _rows(runner, "SELECT derived_from_artifact_code FROM engineering_drawing_revision_artifact WHERE artifact_code = 'GLB-NEW'")[0]
    assert row["derived_from_artifact_code"] == "STEP-OLD"


# ---- link ----

@pytest.mark.parametrize("target_type,target_code", [("ASSET", _ASSET), ("SEAL", _SEAL), ("COMPONENT", _COMPONENT)])
def test_link_target_type_valid_polymorphic_no_fk(runner, target_type, target_code):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L1', 'ENGDRW-1', '{target_type}', '{target_code}', 'APPLIES_TO');"
    )
    row = _rows(runner, "SELECT target_type, target_code FROM engineering_drawing_link WHERE link_code = 'L1'")[0]
    assert row["target_type"] == target_type
    assert row["target_code"] == target_code


def test_link_target_type_invalid_rejected(runner):
    _insert_drawing(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
            "('L1', 'ENGDRW-1', 'BOGUS', 'X', 'APPLIES_TO');"
        )


def test_link_target_code_arbitrary_text_no_fk_error(runner):
    # Polymorphic -- no DB FK on target_code. An unknown/nonexistent
    # target_code must NOT raise (application-layer validation is R4's job).
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        "('L1', 'ENGDRW-1', 'ASSET', 'NO-SUCH-ASSET-CODE', 'APPLIES_TO');"
    )
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link WHERE link_code = 'L1'") == 1


@pytest.mark.parametrize("relationship_type", ["APPLIES_TO", "DEPICTS", "COMPONENT_OF"])
def test_link_relationship_type_valid_values(runner, relationship_type):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L1', 'ENGDRW-1', 'ASSET', '{_ASSET}', '{relationship_type}');"
    )
    row = _rows(runner, "SELECT relationship_type FROM engineering_drawing_link WHERE link_code = 'L1'")[0]
    assert row["relationship_type"] == relationship_type


@pytest.mark.parametrize("relationship_type", ["COMPATIBLE_WITH", "ASSEMBLY_OF", "BOGUS"])
def test_link_relationship_type_excluded_values_rejected(runner, relationship_type):
    _insert_drawing(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
            f"('L1', 'ENGDRW-1', 'ASSET', '{_ASSET}', '{relationship_type}');"
        )


def test_active_duplicate_link_rejected(runner):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L1', 'ENGDRW-1', 'ASSET', '{_ASSET}', 'APPLIES_TO');"
    )
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
            f"('L2', 'ENGDRW-1', 'ASSET', '{_ASSET}', 'APPLIES_TO');"
        )


def test_retracted_link_history_preserved(runner):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L1', 'ENGDRW-1', 'ASSET', '{_ASSET}', 'APPLIES_TO');"
    )
    runner.execute_script(
        "UPDATE engineering_drawing_link SET retracted_at = NOW() WHERE link_code = 'L1';"
    )
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link WHERE link_code = 'L1'") == 1
    row = _rows(runner, "SELECT retracted_at FROM engineering_drawing_link WHERE link_code = 'L1'")[0]
    assert row["retracted_at"] is not None


def test_link_reestablished_after_retraction(runner):
    _insert_drawing(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L1', 'ENGDRW-1', 'ASSET', '{_ASSET}', 'APPLIES_TO');"
    )
    runner.execute_script("UPDATE engineering_drawing_link SET retracted_at = NOW() WHERE link_code = 'L1';")
    # Re-establishing the exact same tuple must succeed now that L1 is retracted.
    runner.execute_script(
        "INSERT INTO engineering_drawing_link (link_code, drawing_code, target_type, target_code, relationship_type) VALUES "
        f"('L2', 'ENGDRW-1', 'ASSET', '{_ASSET}', 'APPLIES_TO');"
    )
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link WHERE drawing_code = 'ENGDRW-1'") == 2


# ---- BOM ----

def test_bom_line_with_known_component(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_bom_line (bom_line_code, revision_code, component_id, quantity) VALUES "
        f"('BOM-1', 'ENGDRWREV-1', '{_COMPONENT}', 2);"
    )
    row = _rows(runner, "SELECT component_id, quantity FROM engineering_drawing_bom_line WHERE bom_line_code = 'BOM-1'")[0]
    assert row["component_id"] == _COMPONENT
    assert float(row["quantity"]) == 2


def test_bom_line_null_component_preserves_description(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    runner.execute_script(
        "INSERT INTO engineering_drawing_bom_line (bom_line_code, revision_code, component_description) VALUES "
        "('BOM-1', 'ENGDRWREV-1', 'As-drawn: unresolved o-ring, item 12');"
    )
    row = _rows(runner, "SELECT component_id, component_description FROM engineering_drawing_bom_line WHERE bom_line_code = 'BOM-1'")[0]
    assert row["component_id"] is None
    assert row["component_description"] == "As-drawn: unresolved o-ring, item 12"


def test_bom_line_invalid_component_fk_rejected(runner):
    _insert_drawing(runner)
    _insert_revision(runner)
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_bom_line (bom_line_code, revision_code, component_id) VALUES "
            "('BOM-1', 'ENGDRWREV-1', 'NO-SUCH-COMPONENT');"
        )


def test_bom_line_invalid_revision_fk_rejected(runner):
    with pytest.raises(psycopg2.Error):
        runner.execute_script(
            "INSERT INTO engineering_drawing_bom_line (bom_line_code, revision_code) VALUES "
            "('BOM-1', 'NO-SUCH-REVISION');"
        )


# ---- existing authorities unchanged / zero data migration ----

def test_existing_authority_tables_unchanged(runner):
    before = (
        _count(runner, "SELECT COUNT(*) FROM asset_registry"),
        _count(runner, "SELECT COUNT(*) FROM seal_registry"),
        _count(runner, "SELECT COUNT(*) FROM internal_component_master"),
        _count(runner, "SELECT COUNT(*) FROM knowledge_source_registry"),
    )
    bootstrap_schema_reapply = _MIGRATION_038.read_text(encoding="utf-8")
    runner.execute_script(bootstrap_schema_reapply)
    after = (
        _count(runner, "SELECT COUNT(*) FROM asset_registry"),
        _count(runner, "SELECT COUNT(*) FROM seal_registry"),
        _count(runner, "SELECT COUNT(*) FROM internal_component_master"),
        _count(runner, "SELECT COUNT(*) FROM knowledge_source_registry"),
    )
    assert before == after


def test_migration_reapply_is_safe(runner):
    # Idempotency -- re-running the whole migration script against a DB
    # that already has it applied must not error and must not duplicate rows.
    migration_sql = _MIGRATION_038.read_text(encoding="utf-8")
    runner.execute_script(migration_sql)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 0


def test_zero_data_after_fresh_migration(runner):
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line") == 0
