"""MWO-LTSA-DRAWING-INPUT-R5C / R5C.1 -- EngineeringDrawingReviewService
against a REAL, disposable, published-port Postgres. Same container/
bootstrap/truncate pattern as
test_engineering_drawing_extraction_staging_service.py (Drawing-R5B).
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
from API.engineering_drawing_review_service import (  # noqa: E402
    CandidateNotFound,
    CandidateNotReviewable,
    EngineeringDrawingReviewService,
    InvalidReviewTransition,
    StaleReviewWrite,
)

_CONTAINER_NAME = "ai5r-test-drawing-review-service-pg"
_USER = "ai5r"
_PASSWORD = "test-drawing-review-service-password"
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
    )
]

_ACTOR = "00000000-0000-0000-0000-000000000001"
_ACTOR_B = "00000000-0000-0000-0000-000000000002"


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
        "TRUNCATE document_field_extraction, engineering_drawing_attribute, engineering_drawing_bom_line, "
        "engineering_drawing_link, engineering_drawing_revision_artifact, engineering_drawing_revision, "
        "engineering_drawing RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status) VALUES "
        "('DFE-1', 'KS-1', 'PDF', 'ENGINEERING_DRAWING_CANDIDATE', 'claude:drawing-extraction-prompt-v1', "
        "'{\"drawing_identity\": {\"drawing_number\": {\"raw_value\": null}, \"title\": {\"raw_value\": \"Test Drawing\"}, "
        "\"manufacturer\": {\"raw_value\": \"John Crane\"}, \"drawing_type\": {\"raw_value\": null}}, "
        "\"attributes\": [{\"concept\": \"SHAFT_DIAMETER\", \"raw_value\": \"4.500\\\"\"}]}'::jsonb, 'PENDING_REVIEW');"
    )
    return r


@pytest.fixture
def service(runner):
    return EngineeringDrawingReviewService(runner)


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


def _review_to_eligible(service):
    """Helper: resolve identity (title+manufacturer) + artifact -- the
    minimum this MWO's own promotion-eligibility rule requires."""
    service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    return service.review_artifact("DFE-1", action="CORRECT", corrected_class="SOURCE_DOCUMENT", reviewed_by=_ACTOR)


# ---- basic fetch ----

def test_get_candidate(service):
    candidate = service.get_candidate("DFE-1")
    assert candidate["status"] == "PENDING_REVIEW"
    assert candidate["reviewed_fields"] is None


def test_get_nonexistent_candidate_raises(service):
    with pytest.raises(CandidateNotFound):
        service.get_candidate("DFE-MISSING")


# ---- extracted_fields immutability ----

def test_extracted_fields_never_mutated_by_review(service, runner):
    before = runner.query_scalar("SELECT extracted_fields::text FROM document_field_extraction WHERE document_field_extraction_id = 'DFE-1'")
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="title", action="CORRECT", corrected_raw_value="Corrected Title", reviewed_by=_ACTOR)
    after = runner.query_scalar("SELECT extracted_fields::text FROM document_field_extraction WHERE document_field_extraction_id = 'DFE-1'")
    assert before == after


# ---- identity field review persistence ----

def test_review_identity_field_persists(service):
    updated = service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}
    assert updated["reviewed_by"] == _ACTOR
    assert updated["reviewed_at"] is not None
    assert updated["status"] == "PENDING_REVIEW"  # status unchanged by a field-level review


def test_partial_review_across_multiple_calls(service):
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    updated = service.review_identity_field("DFE-1", field_name="title", action="CORRECT", corrected_raw_value="New Title", reviewed_by=_ACTOR)
    identity = updated["reviewed_fields"]["drawing_identity"]
    assert identity["manufacturer"] == {"review_status": "ACCEPTED"}
    assert identity["title"] == {"review_status": "CORRECTED", "value": "New Title"}
    # drawing_number/drawing_type still deferred (absent)
    assert "drawing_number" not in identity
    assert "drawing_type" not in identity


def test_review_revision_persists(service):
    updated = service.review_revision("DFE-1", action="CORRECT", corrected_revision="B", corrected_revision_date="2026-06-15", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["revision_candidate"] == {"review_status": "CORRECTED", "revision": "B", "revision_date": "2026-06-15"}


def test_review_attribute_persists(service):
    updated = service.review_attribute("DFE-1", index=0, action="ACCEPT", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["attributes"]["0"] == {"review_status": "ACCEPTED"}


def test_review_reference_persists(service):
    updated = service.review_reference("DFE-1", index=0, action="REJECT", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["references"]["0"] == {"review_status": "REJECTED"}


def test_review_bom_line_persists(service):
    updated = service.review_bom_line("DFE-1", index=1, action="CORRECT", corrected_value={"quantity_raw": "2"}, reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["bom_candidates"]["1"] == {"review_status": "CORRECTED", "value": {"quantity_raw": "2"}}


# ---- artifact review persistence ----

def test_artifact_accept_persists(service):
    updated = service.review_artifact("DFE-1", action="ACCEPT", extracted_class=None, reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["artifact"]["review_status"] == "ACCEPTED"
    assert updated["reviewed_fields"]["artifact"]["knowledge_source_id"] == "KS-1"


def test_artifact_correct_persists(service):
    updated = service.review_artifact("DFE-1", action="CORRECT", corrected_class="DERIVED_CAD", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["artifact"]["value"] == "DERIVED_CAD"


def test_artifact_reject_persists(service):
    updated = service.review_artifact("DFE-1", action="REJECT", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["artifact"]["review_status"] == "REJECTED"
    assert updated["reviewed_fields"]["artifact"]["value"] is None


def test_artifact_defer_persists_as_noop(service):
    updated = service.review_artifact("DFE-1", action="DEFER", reviewed_by=_ACTOR)
    assert updated.get("reviewed_fields") in (None, {})


def test_artifact_source_linkage_preserved(service):
    updated = service.review_artifact("DFE-1", action="CORRECT", corrected_class="SOURCE_DOCUMENT", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["artifact"]["knowledge_source_id"] == "KS-1"


# ---- promotion eligibility combinations ----

def test_identity_and_artifact_resolved_eligible(service):
    _review_to_eligible(service)
    assert service.promotion_eligible("DFE-1") is True


def test_identity_resolved_artifact_deferred_blocked(service):
    service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    assert service.promotion_eligible("DFE-1") is False


def test_artifact_resolved_identity_unresolved_blocked(service):
    service.review_artifact("DFE-1", action="CORRECT", corrected_class="SOURCE_DOCUMENT", reviewed_by=_ACTOR)
    assert service.promotion_eligible("DFE-1") is False


def test_missing_drawing_number_reviewed_as_absent_still_resolves(service):
    service.review_identity_field("DFE-1", field_name="drawing_number", action="REJECT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_artifact("DFE-1", action="CORRECT", corrected_class="SOURCE_DOCUMENT", reviewed_by=_ACTOR)
    assert service.promotion_eligible("DFE-1") is True


def test_revision_unknown_does_not_block_eligibility(service):
    _review_to_eligible(service)  # revision never reviewed at all
    assert service.promotion_eligible("DFE-1") is True


def test_attributes_and_bom_deferred_do_not_block_eligibility(service):
    _review_to_eligible(service)  # attributes/bom never reviewed at all
    assert service.promotion_eligible("DFE-1") is True


def test_artifact_rejected_without_replacement_blocks_eligibility(service):
    service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)
    service.review_artifact("DFE-1", action="REJECT", reviewed_by=_ACTOR)
    assert service.promotion_eligible("DFE-1") is False


# ---- finalize / reject ----

def test_finalize_requires_complete_identity_and_artifact(service):
    with pytest.raises(InvalidReviewTransition):
        service.finalize_review("DFE-1", reviewed_by=_ACTOR)


def test_finalize_succeeds_once_identity_and_artifact_resolved(service):
    _review_to_eligible(service)
    finalized = service.finalize_review("DFE-1", reviewed_by=_ACTOR)
    assert finalized["status"] == "REVIEWED"


def test_reject_candidate(service):
    rejected = service.reject_candidate("DFE-1", reviewed_by=_ACTOR)
    assert rejected["status"] == "REJECTED"


def test_cannot_review_field_after_rejection(service):
    service.reject_candidate("DFE-1", reviewed_by=_ACTOR)
    with pytest.raises(CandidateNotReviewable):
        service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR)


def test_cannot_finalize_after_rejection(service):
    service.reject_candidate("DFE-1", reviewed_by=_ACTOR)
    with pytest.raises(InvalidReviewTransition):
        service.finalize_review("DFE-1", reviewed_by=_ACTOR)


def test_reject_after_reviewed_allowed(service):
    _review_to_eligible(service)
    service.finalize_review("DFE-1", reviewed_by=_ACTOR)
    rejected = service.reject_candidate("DFE-1", reviewed_by=_ACTOR)
    assert rejected["status"] == "REJECTED"


def test_candidate_level_rejection_distinct_from_artifact_reject(service):
    # Rejecting the ARTIFACT sub-field must never touch the candidate's
    # own status (R5C.1 Section 9's own explicit rule).
    updated = service.review_artifact("DFE-1", action="REJECT", reviewed_by=_ACTOR)
    assert updated["status"] == "PENDING_REVIEW"
    assert updated["reviewed_fields"]["artifact"]["review_status"] == "REJECTED"
    # Now reject the WHOLE candidate -- a distinct, separate action.
    rejected = service.reject_candidate("DFE-1", reviewed_by=_ACTOR)
    assert rejected["status"] == "REJECTED"


# ---- review resubmission ----

def test_review_resubmission_same_field_overwrites_own_prior_decision(service):
    service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    updated = service.review_identity_field("DFE-1", field_name="title", action="CORRECT", corrected_raw_value="Revised Title", reviewed_by=_ACTOR)
    assert updated["reviewed_fields"]["drawing_identity"]["title"] == {"review_status": "CORRECTED", "value": "Revised Title"}


# ---- stale concurrent review (optimistic concurrency) ----

def test_stale_review_write_detected_and_rejected(service):
    # Reviewer A reads the candidate...
    stale_candidate = service.get_candidate("DFE-1")
    # ...then Reviewer B reviews and persists a change first.
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR_B)
    # Reviewer A now attempts to persist based on their OWN stale read --
    # the service must detect this and refuse, not silently overwrite B's change.
    with pytest.raises(StaleReviewWrite):
        service._persist_reviewed_fields(
            "DFE-1", {"drawing_identity": {"title": {"review_status": "ACCEPTED"}}},
            reviewed_by=_ACTOR, expected_updated_at=stale_candidate["updated_at"],
        )
    # B's change must survive untouched.
    current = service.get_candidate("DFE-1")
    assert current["reviewed_fields"]["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}


def test_fresh_review_after_stale_rejection_succeeds(service):
    stale_candidate = service.get_candidate("DFE-1")
    service.review_identity_field("DFE-1", field_name="manufacturer", action="ACCEPT", reviewed_by=_ACTOR_B)
    with pytest.raises(StaleReviewWrite):
        service._persist_reviewed_fields(
            "DFE-1", {}, reviewed_by=_ACTOR, expected_updated_at=stale_candidate["updated_at"],
        )
    # Re-fetch (the correct recovery) and retry -- must succeed cleanly.
    fresh = service.review_identity_field("DFE-1", field_name="title", action="ACCEPT", reviewed_by=_ACTOR)
    assert fresh["reviewed_fields"]["drawing_identity"]["title"] == {"review_status": "ACCEPTED"}
    assert fresh["reviewed_fields"]["drawing_identity"]["manufacturer"] == {"review_status": "ACCEPTED"}


# ---- no canonical drawing writes ----

def test_no_canonical_drawing_writes(service, runner):
    _review_to_eligible(service)
    service.finalize_review("DFE-1", reviewed_by=_ACTOR)

    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 0
