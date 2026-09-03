"""MWO-LTSA-HISTORICAL-REVIEW-UI-001 -- router-level proof for the
historical July staging review/resolve/reject/promote layer built over
the EXISTING pipeline (13a970d/5a5e186) and audit foundation (ff4b938).
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_condition_monitoring_reading_repository,
    get_current_user,
    get_historical_pm_cmon_staging_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_record_change_history_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="actor-1", email="a@example.test", organization_id="org-1",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


def _clear():
    app.dependency_overrides.clear()


class FakePumpGateway:
    def get_pump(self, tag_number):
        return {"success": True, "data": {"tag_number": tag_number, "area": "HOC"}}


def _candidate(**overrides):
    base = {
        "document_field_extraction_id": "DFE-1",
        "source_document_id": "PDF-1",
        "source_document_type": "PDF",
        "detected_document_type": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
        "extraction_provider": "deterministic_workbook_table_parser",
        "extracted_fields": {"occurrence_date": "2026-07-01", "asset_type": "PUMP", "quench_temp_de": None},
        "reviewed_fields": None,
        "status": "PENDING_REVIEW",
        "pump_tag_number": "110-P-9A",
        "source_page": None,
    }
    base.update(overrides)
    return base


class FakeStagingRepository:
    def __init__(self, candidate):
        self.candidate = dict(candidate)
        self.apply_review_calls = []
        self.reject_calls = []
        self.mark_saved_calls = []

    def find_by_id(self, candidate_id):
        return dict(self.candidate) if candidate_id == self.candidate["document_field_extraction_id"] else None

    def list_pending(self, detected_document_type=None):
        return self.list_by_status("PENDING_REVIEW", detected_document_type)

    def list_by_status(self, status, detected_document_type=None):
        if detected_document_type and self.candidate["detected_document_type"] != detected_document_type:
            return []
        return [dict(self.candidate)] if self.candidate["status"] == status else []

    def apply_review(self, candidate_id, *, reviewed_fields, reviewed_by, next_status="REVIEWED", pump_tag_number=None):
        self.apply_review_calls.append(
            {"reviewed_fields": dict(reviewed_fields), "reviewed_by": reviewed_by, "pump_tag_number": pump_tag_number}
        )
        self.candidate["reviewed_fields"] = reviewed_fields
        self.candidate["status"] = next_status
        self.candidate["reviewed_by"] = reviewed_by
        if pump_tag_number is not None:
            self.candidate["pump_tag_number"] = pump_tag_number
        return dict(self.candidate)

    def reject(self, candidate_id, *, reviewed_by):
        self.reject_calls.append(reviewed_by)
        self.candidate["status"] = "REJECTED"
        return dict(self.candidate)

    def mark_saved(self, candidate_id):
        self.mark_saved_calls.append(candidate_id)
        self.candidate["status"] = "SAVED"


class FakeMultiStagingRepository:
    """A multi-candidate fake for the bulk-review endpoint -- the
    single-candidate FakeStagingRepository above only ever holds one
    row, which cannot exercise exact-id-targeting or partial-eligibility
    behavior."""

    def __init__(self, candidates):
        self.candidates = {c["document_field_extraction_id"]: dict(c) for c in candidates}
        self.bulk_review_calls = []

    def find_by_id(self, candidate_id):
        c = self.candidates.get(candidate_id)
        return dict(c) if c else None

    def bulk_review_batch_atomic(self, candidate_ids, *, reviewed_by):
        self.bulk_review_calls.append({"candidate_ids": list(candidate_ids), "reviewed_by": reviewed_by})
        updated = []
        for cid in candidate_ids:
            self.candidates[cid]["status"] = "REVIEWED"
            self.candidates[cid]["reviewed_by"] = reviewed_by
            self.candidates[cid]["reviewed_fields"] = self.candidates[cid]["extracted_fields"]
            updated.append(dict(self.candidates[cid]))
        return updated


class FakePMOccurrenceRepository:
    def __init__(self):
        self.create_draft_calls = []

    def create_draft(self, **kwargs):
        self.create_draft_calls.append(kwargs)
        return {"pm_occurrence_code": "PMOCC-NEW", **kwargs}


class FakeCMONRepository:
    def create_draft(self, **kwargs):
        return {"condition_monitoring_reading_code": "CMONR-NEW", **kwargs}


class FakeHistoryRepository:
    def __init__(self):
        self.append_calls = []
        self.rows = []

    def append(self, **kwargs):
        self.append_calls.append(kwargs)
        self.rows.append(kwargs)
        return kwargs

    def list_for_entity(self, entity_type, entity_id):
        return [r for r in self.rows if r["entity_type"] == entity_type and r["entity_id"] == entity_id]


def _override(*, identity, staging, history=None, pm_repo=None, cmon_repo=None):
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
    app.dependency_overrides[get_record_change_history_repository] = lambda: (history or FakeHistoryRepository())
    app.dependency_overrides[get_pm_occurrence_repository] = lambda: (pm_repo or FakePMOccurrenceRepository())
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: (cmon_repo or FakeCMONRepository())


class TestAccess:
    def test_superuser_can_list_and_get(self):
        staging = FakeStagingRepository(_candidate())
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            assert client.get("/api/ltsa/historical-review/candidates").status_code == 200
            assert client.get("/api/ltsa/historical-review/candidates/DFE-1").status_code == 200
        finally:
            _clear()

    def test_tap_admin_can_list_and_get(self):
        staging = FakeStagingRepository(_candidate())
        _override(identity=_identity("TAP_ADMIN"), staging=staging)
        try:
            assert client.get("/api/ltsa/historical-review/candidates").status_code == 200
        finally:
            _clear()

    def test_other_four_roles_denied(self):
        for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            staging = FakeStagingRepository(_candidate())
            _override(identity=_identity(role), staging=staging)
            try:
                response = client.get("/api/ltsa/historical-review/candidates")
                assert response.status_code == 403, f"{role} must be denied"
            finally:
                _clear()


class TestSourceImmutability:
    def test_review_never_touches_extracted_fields_only_reviewed_fields(self):
        candidate = _candidate()
        staging = FakeStagingRepository(candidate)
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            body = {"reviewed_fields": {**candidate["extracted_fields"], "quench_temp_de": 42.0}, "reason": "Recalibrated"}
            client.post("/api/ltsa/historical-review/candidates/DFE-1/review", json=body)
            call = staging.apply_review_calls[0]
            # extracted_fields is never a parameter apply_review accepts at
            # all -- the original source-extracted value has no code path
            # that could overwrite it.
            assert "extracted_fields" not in call
            assert call["reviewed_fields"]["quench_temp_de"] == 42.0
            # original stays exactly as extracted, forever queryable.
            assert staging.candidate["extracted_fields"]["quench_temp_de"] is None
        finally:
            _clear()


class TestReasonRequired:
    def test_correction_without_reason_is_422(self):
        candidate = _candidate()
        staging = FakeStagingRepository(candidate)
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            body = {"reviewed_fields": {**candidate["extracted_fields"], "quench_temp_de": 42.0}}
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/review", json=body)
            assert response.status_code == 422
            assert staging.apply_review_calls == []
        finally:
            _clear()

    def test_plain_confirm_needs_no_reason(self):
        candidate = _candidate()
        staging = FakeStagingRepository(candidate)
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/review", json={})
            assert response.status_code == 200
            assert len(staging.apply_review_calls) == 1
        finally:
            _clear()

    def test_reject_without_reason_is_422(self):
        staging = FakeStagingRepository(_candidate())
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/reject", json={"reason": ""})
            assert response.status_code == 422
        finally:
            _clear()


class TestActorSpoofProtection:
    def test_reviewed_by_is_always_the_authenticated_actor(self):
        candidate = _candidate()
        staging = FakeStagingRepository(candidate)
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            body = {
                "reviewed_fields": {**candidate["extracted_fields"], "quench_temp_de": 42.0},
                "reason": "fix", "reviewed_by": "spoofed", "actor_id": "spoofed",
            }
            client.post("/api/ltsa/historical-review/candidates/DFE-1/review", json=body)
            assert staging.apply_review_calls[0]["reviewed_by"] == "actor-1"
        finally:
            _clear()


class TestNullVsZero:
    def test_null_to_zero_is_flagged_as_a_real_correction(self):
        candidate = _candidate(extracted_fields={"mechseal_temp_de": None})
        staging = FakeStagingRepository(candidate)
        history = FakeHistoryRepository()
        _override(identity=_identity("SUPERUSER"), staging=staging, history=history)
        try:
            body = {"reviewed_fields": {"mechseal_temp_de": 0}, "reason": "confirmed zero reading"}
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/review", json=body)
            assert response.status_code == 200
            assert history.append_calls[0]["old_value"] is None
            assert history.append_calls[0]["new_value"] == "0"
        finally:
            _clear()


class TestPumpResolutionAudit:
    def test_resolving_pump_match_requires_reason_and_is_audited(self):
        candidate = _candidate(pump_tag_number=None, status="PENDING_REVIEW")
        staging = FakeStagingRepository(candidate)
        history = FakeHistoryRepository()
        _override(identity=_identity("TAP_ADMIN"), staging=staging, history=history)
        try:
            no_reason = client.post(
                "/api/ltsa/historical-review/candidates/DFE-1/review",
                json={"pump_tag_number": "110-P-9A"},
            )
            assert no_reason.status_code == 422

            response = client.post(
                "/api/ltsa/historical-review/candidates/DFE-1/review",
                json={"pump_tag_number": "110-P-9A", "reason": "Confirmed against roster, whitespace variant"},
            )
            assert response.status_code == 200
            pump_entries = [c for c in history.append_calls if c["field_name"] == "pump_tag_number"]
            assert len(pump_entries) == 1
            assert pump_entries[0]["new_value"] == "110-P-9A"
            assert pump_entries[0]["reason"] == "Confirmed against roster, whitespace variant"
            assert pump_entries[0]["changed_by"] == "actor-1"
        finally:
            _clear()


class TestPromotion:
    def test_unresolved_pending_review_candidate_cannot_promote(self):
        staging = FakeStagingRepository(_candidate(status="PENDING_REVIEW"))
        pm_repo = FakePMOccurrenceRepository()
        _override(identity=_identity("SUPERUSER"), staging=staging, pm_repo=pm_repo)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/promote")
            assert response.status_code == 422
            assert pm_repo.create_draft_calls == []
        finally:
            _clear()

    def test_reviewed_candidate_with_resolved_pump_promotes(self):
        staging = FakeStagingRepository(_candidate(status="REVIEWED", pump_tag_number="110-P-9A"))
        pm_repo = FakePMOccurrenceRepository()
        _override(identity=_identity("SUPERUSER"), staging=staging, pm_repo=pm_repo)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/promote")
            assert response.status_code == 200
            assert response.json()["data"]["pm_occurrence_code"] == "PMOCC-NEW"
            assert len(pm_repo.create_draft_calls) == 1
            assert pm_repo.create_draft_calls[0]["provenance"] == "HISTORICAL_IMPORT"
            assert staging.mark_saved_calls == ["DFE-1"]
        finally:
            _clear()

    def test_already_saved_candidate_cannot_promote_again(self):
        staging = FakeStagingRepository(_candidate(status="SAVED", pump_tag_number="110-P-9A"))
        pm_repo = FakePMOccurrenceRepository()
        _override(identity=_identity("SUPERUSER"), staging=staging, pm_repo=pm_repo)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/promote")
            assert response.status_code == 409
            assert pm_repo.create_draft_calls == []
        finally:
            _clear()

    def test_finding_candidate_type_is_not_promotable(self):
        staging = FakeStagingRepository(
            _candidate(status="REVIEWED", detected_document_type="HISTORICAL_FINDING_CANDIDATE")
        )
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-1/promote")
            assert response.status_code == 422
        finally:
            _clear()


class TestHistoryReuse:
    def test_superuser_can_read_staging_candidate_history_via_the_reused_endpoint(self):
        history = FakeHistoryRepository()
        history.rows.append({
            "entity_type": "HISTORICAL_STAGING_CANDIDATE", "entity_id": "DFE-1",
            "field_name": "quench_temp_de", "old_value": None, "new_value": "42.0",
        })
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "HISTORICAL_STAGING_CANDIDATE", "entity_id": "DFE-1"},
            )
            assert response.status_code == 200
            assert len(response.json()["data"]) == 1
        finally:
            _clear()

    def test_tap_admin_denied_staging_candidate_history(self):
        history = FakeHistoryRepository()
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "HISTORICAL_STAGING_CANDIDATE", "entity_id": "DFE-1"},
            )
            assert response.status_code == 403
        finally:
            _clear()


class TestBulkReview:
    def test_superuser_bulk_reviews_exact_ids(self):
        staging = FakeMultiStagingRepository([
            _candidate(document_field_extraction_id="DFE-1"),
            _candidate(document_field_extraction_id="DFE-2"),
            _candidate(document_field_extraction_id="DFE-3"),
        ])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1", "DFE-2"]},
            )
            assert response.status_code == 200
            assert response.json()["data"]["reviewed_count"] == 2
            assert sorted(response.json()["data"]["candidate_ids"]) == ["DFE-1", "DFE-2"]
            # exact targeting -- DFE-3 was never named, so it must be untouched
            assert staging.candidates["DFE-3"]["status"] == "PENDING_REVIEW"
            assert staging.bulk_review_calls[0]["candidate_ids"] == ["DFE-1", "DFE-2"]
        finally:
            _clear()

    def test_other_four_roles_denied(self):
        for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
            staging = FakeMultiStagingRepository([_candidate(document_field_extraction_id="DFE-1")])
            _override(identity=_identity(role), staging=staging)
            try:
                response = client.post(
                    "/api/ltsa/historical-review/candidates/bulk-review",
                    json={"candidate_ids": ["DFE-1"]},
                )
                assert response.status_code == 403, f"{role} must be denied"
            finally:
                _clear()

    def test_reviewer_is_always_the_authenticated_actor_never_the_payload(self):
        staging = FakeMultiStagingRepository([_candidate(document_field_extraction_id="DFE-1")])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            # BulkReviewRequest has no reviewed_by field at all -- an
            # extra key is simply ignored by pydantic, never a spoof path.
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1"], "reviewed_by": "spoofed"},
            )
            assert response.status_code == 200
            assert staging.bulk_review_calls[0]["reviewed_by"] == "actor-1"
        finally:
            _clear()

    def test_no_correction_possible_extracted_fields_untouched(self):
        candidate = _candidate(
            document_field_extraction_id="DFE-1",
            extracted_fields={"occurrence_date": "2026-07-01", "quench_temp_de": None},
        )
        staging = FakeMultiStagingRepository([candidate])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1"]},
            )
            assert response.status_code == 200
            assert staging.candidates["DFE-1"]["extracted_fields"]["quench_temp_de"] is None
            assert staging.candidates["DFE-1"]["reviewed_fields"] == staging.candidates["DFE-1"]["extracted_fields"]
        finally:
            _clear()

    def test_empty_candidate_ids_is_422(self):
        staging = FakeMultiStagingRepository([])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review", json={"candidate_ids": []}
            )
            assert response.status_code == 422
        finally:
            _clear()

    def test_duplicate_candidate_ids_is_422(self):
        staging = FakeMultiStagingRepository([_candidate(document_field_extraction_id="DFE-1")])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1", "DFE-1"]},
            )
            assert response.status_code == 422
            assert staging.bulk_review_calls == []
        finally:
            _clear()

    def test_batch_too_large_is_422(self):
        staging = FakeMultiStagingRepository([])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            ids = [f"DFE-{i}" for i in range(1001)]
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review", json={"candidate_ids": ids}
            )
            assert response.status_code == 422
        finally:
            _clear()

    def test_one_ineligible_candidate_fails_the_whole_batch(self):
        staging = FakeMultiStagingRepository([
            _candidate(document_field_extraction_id="DFE-1", status="PENDING_REVIEW"),
            _candidate(document_field_extraction_id="DFE-2", status="REVIEWED"),
        ])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1", "DFE-2"]},
            )
            assert response.status_code == 409
            assert staging.candidates["DFE-1"]["status"] == "PENDING_REVIEW"
            assert staging.bulk_review_calls == []
        finally:
            _clear()

    def test_missing_candidate_id_is_404(self):
        staging = FakeMultiStagingRepository([_candidate(document_field_extraction_id="DFE-1")])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1", "DFE-MISSING"]},
            )
            assert response.status_code == 404
            assert staging.bulk_review_calls == []
        finally:
            _clear()

    def test_non_pm_candidate_fails_the_batch(self):
        staging = FakeMultiStagingRepository([
            _candidate(document_field_extraction_id="DFE-1", detected_document_type="HISTORICAL_CMON_READING_CANDIDATE"),
        ])
        _override(identity=_identity("SUPERUSER"), staging=staging)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1"]},
            )
            assert response.status_code == 409
            assert staging.bulk_review_calls == []
        finally:
            _clear()

    def test_promotion_is_not_performed_by_bulk_review(self):
        staging = FakeMultiStagingRepository([_candidate(document_field_extraction_id="DFE-1")])
        pm_repo = FakePMOccurrenceRepository()
        _override(identity=_identity("SUPERUSER"), staging=staging, pm_repo=pm_repo)
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/bulk-review",
                json={"candidate_ids": ["DFE-1"]},
            )
            assert response.status_code == 200
            assert staging.candidates["DFE-1"]["status"] == "REVIEWED"
            assert pm_repo.create_draft_calls == []
        finally:
            _clear()
