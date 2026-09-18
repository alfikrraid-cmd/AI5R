"""MWO-LTSA-DRAWING-INPUT-R4 -- EngineeringDrawingRepository against a
REAL, disposable, published-port Postgres. Same container/bootstrap/
truncate pattern as test_engineering_drawing_schema.py (Drawing-R3).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.engineering_drawing_repository import (  # noqa: E402
    ArtifactNotFound,
    ComponentNotFound,
    CrossDrawingRevision,
    DrawingNotFound,
    DuplicateActiveLink,
    DuplicatePrimaryArtifact,
    EngineeringDrawingRepository,
    InvalidLinkTarget,
    KnowledgeSourceNotFound,
    RevisionNotFound,
)

_CONTAINER_NAME = "ai5r-test-engineering-drawing-repo-pg"
_USER = "ai5r"
_PASSWORD = "test-engineering-drawing-repo-password"
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
    )
]

_ASSET_HOC = "211-P-13AR"
_ASSET_HSC = "212-P-25A"
_SEAL = "SEAL-1"
_COMPONENT = "CMP-1"
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
        "TRUNCATE engineering_drawing_bom_line, engineering_drawing_link, "
        "engineering_drawing_revision_artifact, engineering_drawing_revision, engineering_drawing, "
        "knowledge_source_registry, internal_component_master, asset_registry, seal_registry, ltsa_pumps "
        "RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_ASSET_HOC}', '{_ASSET_HOC}', 'PUMP', 'HOC', 'Active'), "
        f"('{_ASSET_HSC}', '{_ASSET_HSC}', 'PUMP', 'HSC', 'Active');"
    )
    r.execute_script(f"INSERT INTO seal_registry (seal_code, seal_name) VALUES ('{_SEAL}', 'Test Seal');")
    r.execute_script(
        "INSERT INTO internal_component_master (component_id, component_class, gpn_status, identity_fingerprint, description) "
        f"VALUES ('{_COMPONENT}', 'O_RING', 'GPN_PENDING', 'FP-1', 'Test O-Ring');"
    )
    r.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES "
        "('KS-1', 'DRAWING', 'Source 1'), ('KS-2', 'DRAWING', 'Source 2');"
    )
    return r


@pytest.fixture
def repo(runner):
    return EngineeringDrawingRepository(runner)


# ---- drawing ----

def test_create_get_update_list_drawing(repo):
    created = repo.create_drawing(title="Test Drawing", created_by=_ACTOR)
    fetched = repo.find_drawing(created["drawing_code"])
    assert fetched["title"] == "Test Drawing"
    updated = repo.update_drawing(created["drawing_code"], values={"title": "New Title"}, updated_by=_ACTOR)
    assert updated["title"] == "New Title"
    listing = repo.list_drawings()
    assert listing["total"] == 1


def test_drawing_number_null(repo):
    created = repo.create_drawing(title="X", drawing_number=None, created_by=_ACTOR)
    assert created["drawing_number"] is None


# ---- revision ----

def test_create_multiple_revisions(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    r1 = repo.create_revision(drawing_code=drawing["drawing_code"], revision="A", created_by=_ACTOR)
    r2 = repo.create_revision(drawing_code=drawing["drawing_code"], revision="B", created_by=_ACTOR)
    revisions = repo.list_revisions_for_drawing(drawing["drawing_code"])
    assert len(revisions) == 2
    assert {r1["revision_code"], r2["revision_code"]} == {r["revision_code"] for r in revisions}


def test_revision_null(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], revision=None, created_by=_ACTOR)
    assert revision["revision"] is None


def test_set_valid_current_revision(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], revision="A", created_by=_ACTOR)
    updated = repo.set_current_revision(drawing["drawing_code"], revision["revision_code"], updated_by=_ACTOR)
    assert updated["current_revision_code"] == revision["revision_code"]


def test_reject_cross_drawing_current_revision(repo):
    d1 = repo.create_drawing(title="D1", created_by=_ACTOR)
    d2 = repo.create_drawing(title="D2", created_by=_ACTOR)
    r1 = repo.create_revision(drawing_code=d1["drawing_code"], revision="A", created_by=_ACTOR)
    with pytest.raises(CrossDrawingRevision):
        repo.set_current_revision(d2["drawing_code"], r1["revision_code"], updated_by=_ACTOR)


def test_create_revision_nonexistent_drawing_rejected(repo):
    with pytest.raises(DrawingNotFound):
        repo.create_revision(drawing_code="NO-SUCH-DRAWING", created_by=_ACTOR)


# ---- artifact ----

@pytest.mark.parametrize("artifact_class", ["SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET", "UNKNOWN"])
def test_create_all_artifact_classes(repo, artifact_class):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    artifact = repo.create_artifact(
        revision_code=revision["revision_code"], knowledge_source_id="KS-1", artifact_class=artifact_class, created_by=_ACTOR
    )
    assert artifact["artifact_class"] == artifact_class


def test_artifact_lineage(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    step = repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", artifact_class="DERIVED_CAD", created_by=_ACTOR)
    glb = repo.create_artifact(
        revision_code=revision["revision_code"], knowledge_source_id="KS-2", artifact_class="VIEWER_ASSET",
        derived_from_artifact_code=step["artifact_code"], created_by=_ACTOR,
    )
    assert glb["derived_from_artifact_code"] == step["artifact_code"]


def test_cross_revision_lineage(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    r1 = repo.create_revision(drawing_code=drawing["drawing_code"], revision="A", created_by=_ACTOR)
    r2 = repo.create_revision(drawing_code=drawing["drawing_code"], revision="B", created_by=_ACTOR)
    old_step = repo.create_artifact(revision_code=r1["revision_code"], knowledge_source_id="KS-1", artifact_class="DERIVED_CAD", created_by=_ACTOR)
    new_glb = repo.create_artifact(
        revision_code=r2["revision_code"], knowledge_source_id="KS-2", artifact_class="VIEWER_ASSET",
        derived_from_artifact_code=old_step["artifact_code"], created_by=_ACTOR,
    )
    assert new_glb["derived_from_artifact_code"] == old_step["artifact_code"]


def test_artifact_class_immutable_through_update(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    artifact = repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", artifact_class="DERIVED_CAD", created_by=_ACTOR)
    updated = repo.update_artifact(artifact["artifact_code"], values={"artifact_class": "SOURCE_CAD"}, updated_by=_ACTOR)
    assert updated["artifact_class"] == "DERIVED_CAD"  # attempted change silently dropped


def test_knowledge_source_missing_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    with pytest.raises(KnowledgeSourceNotFound):
        repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="NO-SUCH-KS", created_by=_ACTOR)


def test_duplicate_primary_artifact_class_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", artifact_class="DERIVED_CAD", is_primary=True, created_by=_ACTOR)
    with pytest.raises(DuplicatePrimaryArtifact):
        repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-2", artifact_class="DERIVED_CAD", is_primary=True, created_by=_ACTOR)


def test_derived_from_artifact_missing_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    with pytest.raises(ArtifactNotFound):
        repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", derived_from_artifact_code="NO-SUCH-ARTIFACT", created_by=_ACTOR)


# ---- link ----

def test_create_valid_asset_link(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    assert link["target_type"] == "ASSET"


def test_create_valid_seal_link(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="SEAL", target_code=_SEAL, relationship_type="DEPICTS", created_by=_ACTOR)
    assert link["target_type"] == "SEAL"


def test_create_valid_component_link(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="COMPONENT", target_code=_COMPONENT, relationship_type="COMPONENT_OF", created_by=_ACTOR)
    assert link["target_type"] == "COMPONENT"


def test_invalid_polymorphic_target_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    with pytest.raises(InvalidLinkTarget):
        repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code="NO-SUCH-ASSET", relationship_type="APPLIES_TO", created_by=_ACTOR)


def test_duplicate_active_link_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    with pytest.raises(DuplicateActiveLink):
        repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)


def test_retract_preserves_row(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    retracted = repo.retract_link(link["link_code"], retracted_by=_ACTOR)
    assert retracted["retracted_at"] is not None
    assert repo.find_link(link["link_code"]) is not None


def test_reestablish_link_after_retraction(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    repo.retract_link(link["link_code"], retracted_by=_ACTOR)
    new_link = repo.create_link(drawing_code=drawing["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    assert new_link["link_code"] != link["link_code"]


# ---- BOM ----

def test_bom_with_known_component(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    bom = repo.create_bom_line(revision_code=revision["revision_code"], component_id=_COMPONENT, quantity=2, created_by=_ACTOR)
    assert bom["component_id"] == _COMPONENT


def test_bom_unresolved_component(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    bom = repo.create_bom_line(revision_code=revision["revision_code"], component_description="As-drawn unresolved o-ring", created_by=_ACTOR)
    assert bom["component_id"] is None
    assert bom["component_description"] == "As-drawn unresolved o-ring"


def test_bom_invalid_component_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    with pytest.raises(ComponentNotFound):
        repo.create_bom_line(revision_code=revision["revision_code"], component_id="NO-SUCH-COMPONENT", created_by=_ACTOR)


def test_bom_invalid_revision_rejected(repo):
    with pytest.raises(RevisionNotFound):
        repo.create_bom_line(revision_code="NO-SUCH-REVISION", created_by=_ACTOR)


# ---- verification status ----

@pytest.mark.parametrize("status", ["DRAFT", "UNDER_REVIEW", "VERIFIED", "CANONICAL"])
def test_verification_status_valid_values(repo, status):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], verification_status=status, created_by=_ACTOR)
    assert revision["verification_status"] == status


def test_verification_status_invalid_rejected(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    with pytest.raises(ValueError):
        repo.create_revision(drawing_code=drawing["drawing_code"], verification_status="BOGUS", created_by=_ACTOR)


def test_verification_status_never_auto_promoted(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    assert revision["verification_status"] == "DRAFT"
    repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", created_by=_ACTOR)
    unchanged = repo.find_revision(revision["revision_code"])
    assert unchanged["verification_status"] == "DRAFT"


# ---- area/MA scope ----

def test_list_drawings_area_scope(repo):
    d1 = repo.create_drawing(title="D1", created_by=_ACTOR)
    d2 = repo.create_drawing(title="D2", created_by=_ACTOR)
    repo.create_link(drawing_code=d1["drawing_code"], target_type="ASSET", target_code=_ASSET_HOC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    repo.create_link(drawing_code=d2["drawing_code"], target_type="ASSET", target_code=_ASSET_HSC, relationship_type="APPLIES_TO", created_by=_ACTOR)
    scoped = repo.list_drawings(scope=frozenset({"HOC"}))
    assert scoped["total"] == 1
    assert scoped["data"][0]["drawing_code"] == d1["drawing_code"]


def test_drawing_with_no_asset_link_excluded_for_restricted_identity(repo):
    drawing = repo.create_drawing(title="SealOnly", created_by=_ACTOR)
    repo.create_link(drawing_code=drawing["drawing_code"], target_type="SEAL", target_code=_SEAL, relationship_type="DEPICTS", created_by=_ACTOR)
    scoped = repo.list_drawings(scope=frozenset({"HOC"}))
    assert scoped["total"] == 0


def test_is_drawing_in_scope_unrestricted_always_true(repo):
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    assert repo.is_drawing_in_scope(drawing["drawing_code"], None) is True


# ---- no historical data mutation ----

def test_existing_authority_tables_unchanged_by_drawing_operations(repo):
    before = (
        _row_count(repo, "asset_registry"),
        _row_count(repo, "seal_registry"),
        _row_count(repo, "internal_component_master"),
        _row_count(repo, "knowledge_source_registry"),
    )
    drawing = repo.create_drawing(title="X", created_by=_ACTOR)
    revision = repo.create_revision(drawing_code=drawing["drawing_code"], created_by=_ACTOR)
    repo.create_artifact(revision_code=revision["revision_code"], knowledge_source_id="KS-1", created_by=_ACTOR)
    repo.create_link(drawing_code=drawing["drawing_code"], target_type="SEAL", target_code=_SEAL, relationship_type="DEPICTS", created_by=_ACTOR)
    repo.create_bom_line(revision_code=revision["revision_code"], component_id=_COMPONENT, created_by=_ACTOR)
    after = (
        _row_count(repo, "asset_registry"),
        _row_count(repo, "seal_registry"),
        _row_count(repo, "internal_component_master"),
        _row_count(repo, "knowledge_source_registry"),
    )
    assert before == after


def _row_count(repo: EngineeringDrawingRepository, table: str) -> int:
    return int(repo._runner.query_scalar(f"SELECT COUNT(*) FROM {table}") or "0")
