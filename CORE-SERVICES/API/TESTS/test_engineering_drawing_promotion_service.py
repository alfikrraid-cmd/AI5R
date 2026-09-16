"""MWO-LTSA-DRAWING-INPUT-R5D.1 -- EngineeringDrawingPromotionService
against a REAL, disposable, published-port Postgres. Same
container/bootstrap/truncate pattern as the other Drawing test files, with
one addition (Section 25's own instruction): container cleanup uses
`docker rm -f -v` (removes the anonymous volume too) to avoid leaking
disposable-test volumes across this session's many container runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
from API.engineering_drawing_promotion_service import (  # noqa: E402
    AlreadyPromoted,
    CandidateNotEligible,
    CandidateNotFound,
    CandidateRejected,
    DrawingMatchRequiresReview,
    EngineeringDrawingPromotionService,
    InvalidReviewPayload,
    ReferenceNotFound,
    ScopeDenied,
)

_CONTAINER_NAME = "ai5r-test-drawing-promotion-service-pg"
_USER = "ai5r"
_PASSWORD = "test-drawing-promotion-service-password"
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
_ASSET = "211-P-13AR"
_ASSET_OTHER_AREA = "212-P-25A"
_SEAL = "SEAL-1"
_COMPONENT = "CMP-1"


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", "-v", _CONTAINER_NAME], capture_output=True, text=True)
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
        subprocess.run(["docker", "rm", "-f", "-v", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE engineering_drawing_promotion, engineering_drawing_attribute, engineering_drawing_bom_line, "
        "engineering_drawing_link, engineering_drawing_revision_artifact, engineering_drawing_revision, "
        "engineering_drawing, document_field_extraction, knowledge_source_registry, internal_component_master, "
        "asset_registry, seal_registry RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        "INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_ASSET}', '{_ASSET}', 'PUMP', 'HOC', 'Active'), "
        f"('{_ASSET_OTHER_AREA}', '{_ASSET_OTHER_AREA}', 'PUMP', 'HSC', 'Active');"
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
def config(pg_port):
    return DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)


@pytest.fixture
def service(config):
    return EngineeringDrawingPromotionService(config)


def _rows(runner, sql):
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


# ---- payload builders ----

def _extracted(
    title="Test Drawing", manufacturer="John Crane", drawing_number=None, drawing_type=None,
    revision=None, revision_date=None, attributes=None, bom=None, references=None,
):
    return {
        "drawing_identity": {
            "title": {"raw_value": title},
            "manufacturer": {"raw_value": manufacturer},
            "drawing_number": {"raw_value": drawing_number},
            "drawing_type": {"raw_value": drawing_type},
        },
        "revision_candidate": {"revision": revision, "revision_date": revision_date},
        "attributes": attributes or [],
        "bom_candidates": bom or [],
        "references": references or [],
    }


def _accept():
    return {"review_status": "ACCEPTED"}


def _correct(value):
    return {"review_status": "CORRECTED", "value": value}


def _reject():
    return {"review_status": "REJECTED"}


def _correct_revision(revision, revision_date=None):
    # apply_revision_review's real CORRECTED shape -- "revision"/
    # "revision_date" are top-level siblings of "review_status", NOT
    # nested under a "value" key (unlike identity/attribute/BOM CORRECT).
    return {"review_status": "CORRECTED", "revision": revision, "revision_date": revision_date}


_ELIGIBLE_IDENTITY = {"title": _accept(), "manufacturer": _accept()}
_ARTIFACT_SOURCE_DOC = {"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}


def _reviewed(identity=None, revision=None, artifact=None, attributes=None, bom=None, references=None, versioned=True):
    rf: dict = {}
    if versioned:
        rf["review_schema_version"] = "drawing-review-v1"
    if identity is not None:
        rf["drawing_identity"] = identity
    if revision is not None:
        rf["revision_candidate"] = revision
    if artifact is not None:
        rf["artifact"] = artifact
    if attributes is not None:
        rf["attributes"] = attributes
    if bom is not None:
        rf["bom_candidates"] = bom
    if references is not None:
        rf["references"] = references
    return rf


def _eligible_reviewed(**kwargs):
    kwargs.setdefault("identity", _ELIGIBLE_IDENTITY)
    kwargs.setdefault("artifact", _ARTIFACT_SOURCE_DOC)
    return _reviewed(**kwargs)


def _seed_candidate(runner, candidate_id, *, source_document_id="KS-1", extracted=None, reviewed=None, status="REVIEWED"):
    extracted = extracted if extracted is not None else _extracted()
    reviewed_sql = "NULL" if reviewed is None else f"'{json.dumps(reviewed)}'::jsonb"
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, reviewed_fields, status) VALUES "
        f"('{candidate_id}', '{source_document_id}', 'PDF', 'ENGINEERING_DRAWING_CANDIDATE', "
        f"'claude:drawing-extraction-prompt-v1', '{json.dumps(extracted)}'::jsonb, {reviewed_sql}, '{status}');"
    )


def _candidate_status(runner, candidate_id):
    return _rows(runner, f"SELECT status FROM document_field_extraction WHERE document_field_extraction_id = '{candidate_id}'")[0]["status"]


def _canonical_counts(runner):
    return {
        "drawing": _count(runner, "SELECT COUNT(*) FROM engineering_drawing"),
        "revision": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision"),
        "artifact": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact"),
        "attribute": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute"),
        "bom": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line"),
        "link": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link"),
        "promotion": _count(runner, "SELECT COUNT(*) FROM engineering_drawing_promotion"),
    }


# =====================================================================
# 01-06: drawing match
# =====================================================================

def test_01_new_drawing(service, runner):
    _seed_candidate(
        runner, "DFE-1",
        extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-100"),
        reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}),
    )
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["promotion_status"] == "PROMOTED"
    assert result["drawing_match"] == "NEW_DRAWING"
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 1


def test_02_existing_exact_drawing_reused(service, runner):
    runner.execute_script("INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number) VALUES ('D-EXIST', 'Original Title', 'John Crane', 'DWG-100');")
    _seed_candidate(
        runner, "DFE-1",
        extracted=_extracted(manufacturer="JOHN CRANE", drawing_number="DWG-100"),
        reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}),
    )
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["drawing_match"] == "EXACT_MATCH"
    assert result["drawing_code"] == "D-EXIST"
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 1


def test_03_possible_drawing_match_blocked(service, runner):
    runner.execute_script("INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number) VALUES ('D-EXIST', 'Original Title', 'John Crane', 'DWG-100');")
    _seed_candidate(
        runner, "DFE-1",
        extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-100"),
        reviewed=_eligible_reviewed(identity={"title": _accept(), "manufacturer": _reject(), "drawing_number": _accept()}),
    )
    with pytest.raises(DrawingMatchRequiresReview):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 1


def test_04_ambiguous_drawing_blocked_multiple_existing(service, runner):
    runner.execute_script(
        "INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number) VALUES "
        "('D-A', 'A', 'John Crane', 'DWG-100'), ('D-B', 'B', 'Flowserve', 'DWG-100');"
    )
    _seed_candidate(
        runner, "DFE-1",
        extracted=_extracted(manufacturer="Unknown Co", drawing_number="DWG-100"),
        reviewed=_eligible_reviewed(identity={"title": _accept(), "manufacturer": _reject(), "drawing_number": _accept()}),
    )
    with pytest.raises(DrawingMatchRequiresReview):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 2


def test_05_drawing_number_null_creates_new_drawing(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(drawing_number=None), reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["drawing_match"] == "NEW_DRAWING"
    row = _rows(runner, f"SELECT drawing_number FROM engineering_drawing WHERE drawing_code = '{result['drawing_code']}'")[0]
    assert row["drawing_number"] is None


def test_06_drawing_number_null_retry_deterministic(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(drawing_number=None), reviewed=_eligible_reviewed())
    first = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted) as exc_info:
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert exc_info.value.result["drawing_code"] == first["drawing_code"]
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 1


# =====================================================================
# 07-10: revision
# =====================================================================

def test_07_new_revision(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(revision="A"), reviewed=_eligible_reviewed(revision=_correct_revision("A")))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["revision_match"] == "NEW_REVISION"


def test_08_existing_revision_reused(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-1", revision="A"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}, revision=_correct_revision("A")))
    first = service.promote_candidate("DFE-1", promoted_by=_ACTOR)

    _seed_candidate(runner, "DFE-2", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-1", revision="A"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}, revision=_correct_revision("A"),
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_CAD", "knowledge_source_id": "KS-2"}))
    second = service.promote_candidate("DFE-2", promoted_by=_ACTOR)
    assert second["revision_match"] == "EXACT_MATCH"
    assert second["revision_code"] == first["revision_code"]
    assert second["drawing_code"] == first["drawing_code"]


def test_09_null_revision_creates_own_row(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(revision=None), reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT revision FROM engineering_drawing_revision WHERE revision_code = '{result['revision_code']}'")[0]
    assert row["revision"] is None


def test_10_null_revision_retry_deterministic(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(revision=None), reviewed=_eligible_reviewed())
    first = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted) as exc_info:
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert exc_info.value.result["revision_code"] == first["revision_code"]


# =====================================================================
# 11-15: artifact classes
# =====================================================================

@pytest.mark.parametrize("artifact_class", ["SOURCE_DOCUMENT", "SOURCE_CAD", "DERIVED_CAD", "VIEWER_ASSET", "UNKNOWN"])
def test_11_15_artifact_classes(service, runner, artifact_class):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(artifact={"review_status": "CORRECTED", "value": artifact_class, "knowledge_source_id": "KS-1"}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT artifact_class FROM engineering_drawing_revision_artifact WHERE artifact_code = '{result['artifact_codes'][0]}'")[0]
    assert row["artifact_class"] == artifact_class


# =====================================================================
# 16-21: attributes
# =====================================================================

def test_16_accepted_attribute_promoted(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "raw_value": '4.500"', "value_numeric": 4.5, "unit": "in"}]),
                     reviewed=_eligible_reviewed(attributes={"0": _accept()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert len(result["attribute_codes"]) == 1
    row = _rows(runner, f"SELECT attribute_concept, value_numeric, verification_status FROM engineering_drawing_attribute WHERE attribute_code = '{result['attribute_codes'][0]}'")[0]
    assert row["attribute_concept"] == "SHAFT_DIAMETER"
    assert row["verification_status"] == "VERIFIED"


def test_17_corrected_attribute_promoted(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "raw_value": "4", "value_numeric": 4.0}]),
                     reviewed=_eligible_reviewed(attributes={"0": _correct({"concept": "SHAFT_DIAMETER", "value_numeric": 4.5, "unit": "in"})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT value_numeric, unit FROM engineering_drawing_attribute WHERE attribute_code = '{result['attribute_codes'][0]}'")[0]
    assert float(row["value_numeric"]) == 4.5
    assert row["unit"] == "in"


def test_18_rejected_attribute_omitted(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "value_numeric": 4.5}]),
                     reviewed=_eligible_reviewed(attributes={"0": _reject()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["attribute_codes"] == []
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 0


def test_19_deferred_attribute_omitted(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "value_numeric": 4.5}]),
                     reviewed=_eligible_reviewed())  # attributes never reviewed at all
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["attribute_codes"] == []


def test_20_same_concept_multiple_attributes_preserved(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[
        {"concept": "PORT_SIZE", "value_text": "DE 2in"}, {"concept": "PORT_SIZE", "value_text": "NDE 1in"},
    ]), reviewed=_eligible_reviewed(attributes={"0": _accept(), "1": _accept()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert len(result["attribute_codes"]) == 2
    assert len(set(result["attribute_codes"])) == 2


def test_21_attribute_retry_no_duplicate(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "value_numeric": 4.5}]),
                     reviewed=_eligible_reviewed(attributes={"0": _accept()}))
    first = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 1


# =====================================================================
# 22-25: BOM
# =====================================================================

def test_22_unresolved_bom_component_preserved(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(bom=[{"description": "O-Ring Seal", "quantity_raw": "2"}]),
                     reviewed=_eligible_reviewed(bom={"0": _accept()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT component_id, component_description, quantity FROM engineering_drawing_bom_line WHERE bom_line_code = '{result['bom_line_codes'][0]}'")[0]
    assert row["component_id"] is None
    assert row["component_description"] == "O-Ring Seal"
    assert float(row["quantity"]) == 2.0


def test_23_exact_bom_component_resolved(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(bom=[{"description": "O-Ring"}]),
                     reviewed=_eligible_reviewed(bom={"0": _correct({"component_id": _COMPONENT, "component_description": "O-Ring", "quantity": 2})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT component_id FROM engineering_drawing_bom_line WHERE bom_line_code = '{result['bom_line_codes'][0]}'")[0]
    assert row["component_id"] == _COMPONENT


def test_24_rejected_bom_omitted(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(bom=[{"description": "O-Ring"}]), reviewed=_eligible_reviewed(bom={"0": _reject()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["bom_line_codes"] == []


def test_25_bom_retry_no_duplicate(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(bom=[{"description": "O-Ring"}]), reviewed=_eligible_reviewed(bom={"0": _accept()}))
    service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line") == 1


def test_25b_explicit_invalid_component_id_never_downgraded_to_null(service, runner):
    # R5D.1A Section 3: an EXPLICITLY reviewed/resolved component_id that
    # no longer exists must never be silently swapped for NULL -- it is a
    # genuine data-integrity problem, not a "downgrade to unresolved."
    _seed_candidate(runner, "DFE-1", extracted=_extracted(bom=[{"description": "O-Ring"}]),
                     reviewed=_eligible_reviewed(bom={"0": _correct({"component_id": "NO-SUCH-COMPONENT", "component_description": "O-Ring"})}))
    with pytest.raises(ReferenceNotFound):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line") == 0


def test_25c_invalid_explicit_component_id_rolls_back_whole_promotion(service, runner):
    # Section 4: prove full atomic rollback when the BOM-integrity check
    # fails AFTER earlier canonical writes (drawing/revision/artifact/
    # attribute) have already happened in the SAME transaction.
    _seed_candidate(
        runner, "DFE-1",
        extracted=_extracted(
            manufacturer="John Crane", drawing_number="DWG-ROLLBACK",
            attributes=[{"concept": "SHAFT_DIAMETER", "value_numeric": 4.5}],
            bom=[{"description": "O-Ring"}],
        ),
        reviewed=_eligible_reviewed(
            identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()},
            attributes={"0": _accept()},
            bom={"0": _correct({"component_id": "NO-SUCH-COMPONENT", "component_description": "O-Ring"})},
        ),
    )
    with pytest.raises(ReferenceNotFound):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)

    assert _candidate_status(runner, "DFE-1") == "REVIEWED"
    counts = _canonical_counts(runner)
    assert counts == {"drawing": 0, "revision": 0, "artifact": 0, "attribute": 0, "bom": 0, "link": 0, "promotion": 0}


# =====================================================================
# 26-32: references / links
# =====================================================================

def test_26_explicit_asset_link(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "ASSET", "target_code": _ASSET, "relationship_type": "APPLIES_TO"})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert len(result["link_codes"]) == 1
    row = _rows(runner, f"SELECT target_type, target_code, relationship_type FROM engineering_drawing_link WHERE link_code = '{result['link_codes'][0]}'")[0]
    assert row == {"target_type": "ASSET", "target_code": _ASSET, "relationship_type": "APPLIES_TO"}


def test_27_explicit_seal_link(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "SEAL", "target_code": _SEAL, "relationship_type": "DEPICTS"})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert len(result["link_codes"]) == 1


def test_28_explicit_component_link(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "COMPONENT", "target_code": _COMPONENT, "relationship_type": "COMPONENT_OF"})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert len(result["link_codes"]) == 1


def test_29_possible_reference_not_linked(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _accept()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["link_codes"] == []
    assert any("not linked" in w["message"] for w in result["warnings"])


def test_30_missing_reference_target_blocks_entire_promotion(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "ASSET", "target_code": "NO-SUCH-ASSET", "relationship_type": "APPLIES_TO"})}))
    with pytest.raises(ReferenceNotFound):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _canonical_counts(runner)["drawing"] == 0


def test_31_bad_relationship_blocks_entire_promotion(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "ASSET", "target_code": _ASSET, "relationship_type": "BOGUS"})}))
    with pytest.raises(InvalidReviewPayload):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _canonical_counts(runner)["drawing"] == 0


def test_32_scope_denied_rolls_back_everything(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "SEAL", "target_code": _SEAL, "relationship_type": "DEPICTS"})}))
    with pytest.raises(ScopeDenied):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR, actor_scope=frozenset({"HOC"}))
    counts = _canonical_counts(runner)
    assert counts["drawing"] == 0 and counts["link"] == 0
    assert _candidate_status(runner, "DFE-1") == "REVIEWED"


def test_32b_scope_allowed_via_own_asset_reference(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "ASSET", "target_code": _ASSET, "relationship_type": "APPLIES_TO"})}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR, actor_scope=frozenset({"HOC"}))
    assert result["promotion_status"] == "PROMOTED"


def test_32c_scope_allowed_globally_when_none(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR, actor_scope=None)
    assert result["promotion_status"] == "PROMOTED"


# =====================================================================
# 33-36: entry gate
# =====================================================================

def test_33_malformed_review_blocked(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(identity={"title": _correct(None), "manufacturer": _accept()}))
    with pytest.raises(InvalidReviewPayload):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)


def test_34_unversioned_review_blocked(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(versioned=False))
    with pytest.raises(InvalidReviewPayload):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)


def test_35_rejected_candidate_blocked(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(), status="REJECTED")
    with pytest.raises(CandidateRejected):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)


def test_36_non_eligible_reviewed_candidate_blocked(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_reviewed(identity=_ELIGIBLE_IDENTITY))  # artifact never reviewed
    with pytest.raises(CandidateNotEligible):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)


def test_candidate_not_found(service):
    with pytest.raises(CandidateNotFound):
        service.promote_candidate("DFE-MISSING", promoted_by=_ACTOR)


# =====================================================================
# 37-40: idempotency & concurrency
# =====================================================================

def test_37_saved_replay(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    first = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted) as exc_info:
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert exc_info.value.result["idempotent_replay"] is True
    assert exc_info.value.result["drawing_code"] == first["drawing_code"]
    assert _canonical_counts(runner)["promotion"] == 1


def test_38_same_candidate_concurrent_promotion(runner, config):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())

    def _attempt():
        svc = EngineeringDrawingPromotionService(config)
        try:
            return ("ok", svc.promote_candidate("DFE-1", promoted_by=_ACTOR))
        except AlreadyPromoted as exc:
            return ("already", exc.result)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _attempt(), range(2)))

    outcomes = [kind for kind, _ in results]
    assert outcomes.count("ok") == 1
    assert outcomes.count("already") == 1
    assert _canonical_counts(runner)["promotion"] == 1
    assert _canonical_counts(runner)["drawing"] == 1


def _run_concurrently(config, candidate_ids, *, timeout=30):
    """Real two-thread, two-independent-connection concurrent promotion.
    A threading.Barrier maximizes overlap around the moment both threads
    actually start their own promote_candidate() call -- true guaranteed
    same-instant execution isn't possible from Python threads (GIL +
    separate TCP round-trips introduce jitter regardless), but the whole
    point of the deterministic-code + FOR UPDATE + ON CONFLICT DO NOTHING
    design is that CORRECTNESS never depends on hitting an exact race
    window -- it must hold under ANY interleaving. Bounded timeout
    (Section 7): a hung future here means a real deadlock/lock-timeout,
    which must FAIL the test, never hang indefinitely."""
    barrier = threading.Barrier(len(candidate_ids))
    results: dict[str, tuple[str, object]] = {}
    lock = threading.Lock()

    def _attempt(candidate_id):
        svc = EngineeringDrawingPromotionService(config)
        barrier.wait(timeout=timeout)
        try:
            outcome = ("ok", svc.promote_candidate(candidate_id, promoted_by=_ACTOR))
        except AlreadyPromoted as exc:
            outcome = ("already", exc.result)
        with lock:
            results[candidate_id] = outcome
        return outcome

    with ThreadPoolExecutor(max_workers=len(candidate_ids)) as pool:
        futures = [pool.submit(_attempt, cid) for cid in candidate_ids]
        for future in futures:
            future.result(timeout=timeout)  # bounded -- a real deadlock raises TimeoutError, failing the test
    return results


def test_39_real_concurrent_two_candidates_same_drawing(service, runner, config):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-9"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()},
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}))
    _seed_candidate(runner, "DFE-2", extracted=_extracted(manufacturer="JOHN CRANE", drawing_number="DWG-9"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()},
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_CAD", "knowledge_source_id": "KS-2"}))

    results = _run_concurrently(config, ["DFE-1", "DFE-2"])

    assert set(results) == {"DFE-1", "DFE-2"}
    # Both must complete safely -- either a real PROMOTED result, or (if
    # one thread's own transaction happened to commit before the other's
    # own candidate-row FOR UPDATE releases, which this same-drawing/
    # DIFFERENT-candidate scenario does not itself serialize on, unlike
    # the same-candidate case) a clean AlreadyPromoted is never expected
    # here since these are two DISTINCT candidate_ids -- both threads must
    # report "ok".
    assert all(kind == "ok" for kind, _ in results.values())
    r1, r2 = results["DFE-1"][1], results["DFE-2"][1]

    assert r1["drawing_code"] == r2["drawing_code"]
    assert _canonical_counts(runner)["drawing"] == 1
    assert _canonical_counts(runner)["promotion"] == 2
    assert _candidate_status(runner, "DFE-1") == "SAVED"
    assert _candidate_status(runner, "DFE-2") == "SAVED"
    # Each candidate's own distinct provenance survives -- not collapsed.
    assert r1["artifact_codes"][0] != r2["artifact_codes"][0]
    artifact_ks = {row["knowledge_source_id"] for row in _rows(runner, "SELECT knowledge_source_id FROM engineering_drawing_revision_artifact")}
    assert artifact_ks == {"KS-1", "KS-2"}

    # Section 8: replay both individually -- idempotent, canonical counts unchanged.
    before = _canonical_counts(runner)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-2", promoted_by=_ACTOR)
    assert _canonical_counts(runner) == before


def test_40_real_concurrent_two_candidates_same_revision(service, runner, config):
    common_identity = {**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-9", revision="A"),
                     reviewed=_eligible_reviewed(identity=common_identity, revision=_correct_revision("A"),
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}))
    _seed_candidate(runner, "DFE-2", extracted=_extracted(manufacturer="JOHN CRANE", drawing_number="DWG-9", revision="A"),
                     reviewed=_eligible_reviewed(identity=common_identity, revision=_correct_revision("A"),
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_CAD", "knowledge_source_id": "KS-2"}))

    results = _run_concurrently(config, ["DFE-1", "DFE-2"])

    assert all(kind == "ok" for kind, _ in results.values())
    r1, r2 = results["DFE-1"][1], results["DFE-2"][1]

    assert r1["drawing_code"] == r2["drawing_code"]
    assert r1["revision_code"] == r2["revision_code"]
    assert _canonical_counts(runner)["drawing"] == 1
    assert _canonical_counts(runner)["revision"] == 1
    assert _canonical_counts(runner)["artifact"] == 2
    assert _canonical_counts(runner)["promotion"] == 2
    assert _candidate_status(runner, "DFE-1") == "SAVED"
    assert _candidate_status(runner, "DFE-2") == "SAVED"

    before = _canonical_counts(runner)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    with pytest.raises(AlreadyPromoted):
        service.promote_candidate("DFE-2", promoted_by=_ACTOR)
    assert _canonical_counts(runner) == before


# =====================================================================
# 41-43: transaction integrity
# =====================================================================

def test_41_halfway_failure_complete_rollback(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(attributes=[{"concept": "SHAFT_DIAMETER", "value_numeric": 4.5}]),
                     reviewed=_eligible_reviewed(attributes={"0": _accept()},
                                                  references={"0": _correct({"target_type": "ASSET", "target_code": "NO-SUCH-ASSET", "relationship_type": "APPLIES_TO"})}))
    with pytest.raises(ReferenceNotFound):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    counts = _canonical_counts(runner)
    assert all(v == 0 for v in counts.values())


def test_42_candidate_remains_reviewed_on_rollback(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed(references={"0": _correct({"target_type": "ASSET", "target_code": "NO-SUCH-ASSET", "relationship_type": "APPLIES_TO"})}))
    with pytest.raises(ReferenceNotFound):
        service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _candidate_status(runner, "DFE-1") == "REVIEWED"


def test_43_saved_only_after_all_writes_succeed(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    assert _candidate_status(runner, "DFE-1") == "REVIEWED"
    service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _candidate_status(runner, "DFE-1") == "SAVED"


# =====================================================================
# 44-46: canonical conflict / current revision
# =====================================================================

def test_44_existing_drawing_metadata_not_overwritten(service, runner):
    runner.execute_script("INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number) VALUES ('D-EXIST', 'Original Title', 'John Crane', 'DWG-100');")
    _seed_candidate(runner, "DFE-1", extracted=_extracted(title="Different Title", manufacturer="John Crane", drawing_number="DWG-100"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}))
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, "SELECT title FROM engineering_drawing WHERE drawing_code = 'D-EXIST'")[0]
    assert row["title"] == "Original Title"
    assert any(w["field"] == "title" for w in result["warnings"])


def test_45_existing_current_revision_unchanged(service, runner):
    runner.execute_script("INSERT INTO engineering_drawing (drawing_code, title, manufacturer, drawing_number, current_revision_code) VALUES ('D-EXIST', 'T', 'John Crane', 'DWG-100', NULL);")
    runner.execute_script("INSERT INTO engineering_drawing_revision (revision_code, drawing_code, revision) VALUES ('R-OLD', 'D-EXIST', 'A');")
    runner.execute_script("UPDATE engineering_drawing SET current_revision_code = 'R-OLD' WHERE drawing_code = 'D-EXIST';")
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-100", revision="B"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}, revision=_correct_revision("B")))
    service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, "SELECT current_revision_code FROM engineering_drawing WHERE drawing_code = 'D-EXIST'")[0]
    assert row["current_revision_code"] == "R-OLD"


def test_46_new_drawing_first_revision_becomes_current(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, f"SELECT current_revision_code FROM engineering_drawing WHERE drawing_code = '{result['drawing_code']}'")[0]
    assert row["current_revision_code"] == result["revision_code"]


# =====================================================================
# 47-50: coexistence / storage / legacy
# =====================================================================

def test_47_type8b1_source_and_derived_coexist(service, runner):
    common_identity = {**_ELIGIBLE_IDENTITY, "drawing_number": _accept()}
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-8B1", revision="A"),
                     reviewed=_eligible_reviewed(identity=common_identity, revision=_correct_revision("A"),
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}))
    _seed_candidate(runner, "DFE-2", extracted=_extracted(manufacturer="John Crane", drawing_number="DWG-8B1", revision="A"),
                     reviewed=_eligible_reviewed(identity=common_identity, revision=_correct_revision("A"),
                                                  artifact={"review_status": "CORRECTED", "value": "DERIVED_CAD", "knowledge_source_id": "KS-2"}))
    r1 = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    r2 = service.promote_candidate("DFE-2", promoted_by=_ACTOR)
    assert r1["revision_code"] == r2["revision_code"]
    classes = {row["artifact_class"] for row in _rows(runner, f"SELECT artifact_class FROM engineering_drawing_revision_artifact WHERE revision_code = '{r1['revision_code']}'")}
    assert classes == {"SOURCE_DOCUMENT", "DERIVED_CAD"}


def test_48_same_knowledge_source_different_candidates_not_collapsed(service, runner):
    _seed_candidate(runner, "DFE-1", extracted=_extracted(manufacturer="A", drawing_number="D1"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()},
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}))
    _seed_candidate(runner, "DFE-2", extracted=_extracted(manufacturer="B", drawing_number="D2"),
                     reviewed=_eligible_reviewed(identity={**_ELIGIBLE_IDENTITY, "drawing_number": _accept()},
                                                  artifact={"review_status": "CORRECTED", "value": "SOURCE_DOCUMENT", "knowledge_source_id": "KS-1"}))
    r1 = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    r2 = service.promote_candidate("DFE-2", promoted_by=_ACTOR)
    assert r1["artifact_codes"][0] != r2["artifact_codes"][0]
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact WHERE knowledge_source_id = 'KS-1'") == 2


def test_49_object_storage_key_null_succeeds(service, runner):
    row = _rows(runner, "SELECT object_storage_key FROM knowledge_source_registry WHERE knowledge_source_id = 'KS-1'")[0]
    assert row["object_storage_key"] is None
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert result["promotion_status"] == "PROMOTED"


def test_50_legacy_seal_engineering_document_untouched(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM seal_engineering_document") == 0


# =====================================================================
# 51-52: promotion spine
# =====================================================================

def test_51_promotion_spine_exactly_one_row(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_promotion") == 1
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_promotion WHERE candidate_id = 'DFE-1'") == 1


def test_52_promotion_composite_fk_context_correct(service, runner):
    _seed_candidate(runner, "DFE-1", reviewed=_eligible_reviewed())
    result = service.promote_candidate("DFE-1", promoted_by=_ACTOR)
    row = _rows(runner, "SELECT drawing_code, revision_code, artifact_code FROM engineering_drawing_promotion WHERE candidate_id = 'DFE-1'")[0]
    assert row["drawing_code"] == result["drawing_code"]
    assert row["revision_code"] == result["revision_code"]
    assert row["artifact_code"] == result["artifact_codes"][0]
