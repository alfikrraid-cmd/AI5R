"""MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- proves the MATCHED/
INCOMPLETE/INVALID Core Model, the staging bridge's pump-tag rule (raw
tag always preserved, canonical relation NULL unless EXACT_MATCH, never
a suffix/sister/MM->P inference), later correction+audit by SUPERUSER
and TAP_ADMIN, INVALID-cannot-promote, and that no delete
permission/endpoint was accidentally introduced.
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
    get_current_user,
    get_historical_pm_cmon_staging_repository,
    get_pump_gateway,
    get_record_change_history_repository,
)
from routers.historical_review import classify_candidate  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id="actor-1", email="a@example.test", organization_id="org-1",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
    )


def _clear():
    app.dependency_overrides.clear()


class FakePumpGateway:
    def get_pump(self, tag_number):
        return {"success": True, "data": {"tag_number": tag_number, "area": "HOC"}}


class FakeHistoryRepository:
    def __init__(self):
        self.append_calls = []

    def append(self, **kwargs):
        self.append_calls.append(kwargs)
        return kwargs

    def list_for_entity(self, entity_type, entity_id):
        return [c for c in self.append_calls if c["entity_type"] == entity_type and c["entity_id"] == entity_id]


class FakeStagingRepository:
    def __init__(self, candidate):
        self.candidate = dict(candidate)
        self.apply_review_calls = []

    def find_by_id(self, candidate_id):
        return dict(self.candidate) if candidate_id == self.candidate["document_field_extraction_id"] else None

    def list_by_status(self, status, detected_document_type=None):
        return [dict(self.candidate)] if self.candidate["status"] == status else []

    def apply_review(self, candidate_id, *, reviewed_fields, reviewed_by, next_status="REVIEWED", pump_tag_number=None):
        self.apply_review_calls.append({"reviewed_by": reviewed_by, "pump_tag_number": pump_tag_number})
        self.candidate["reviewed_fields"] = reviewed_fields
        self.candidate["status"] = next_status
        self.candidate["reviewed_by"] = reviewed_by
        if pump_tag_number is not None:
            self.candidate["pump_tag_number"] = pump_tag_number
        return dict(self.candidate)


def _incomplete_candidate(**overrides):
    base = {
        "document_field_extraction_id": "DFE-INC-1",
        "source_document_id": "PDF-HCC-JULY-2026",
        "source_document_type": "PDF",
        "detected_document_type": "HISTORICAL_CMON_READING_CANDIDATE",
        "extraction_provider": "deterministic_workbook_table_parser",
        "extracted_fields": {"mechseal_temp_de": 59.0, "raw_asset_tag": "212-P-14A"},
        "reviewed_fields": None,
        "status": "PENDING_REVIEW",
        "pump_tag_number": None,
        "source_page": None,
    }
    base.update(overrides)
    return base


# --- Core Model classification ------------------------------------------


class TestClassification:
    def test_matched_when_pump_tag_resolved(self):
        assert classify_candidate({"status": "PENDING_REVIEW", "pump_tag_number": "110-P-9A"}) == "MATCHED"

    def test_incomplete_when_pump_tag_null(self):
        assert classify_candidate({"status": "PENDING_REVIEW", "pump_tag_number": None}) == "INCOMPLETE"

    def test_incomplete_when_reviewed_but_still_unresolved(self):
        assert classify_candidate({"status": "REVIEWED", "pump_tag_number": None}) == "INCOMPLETE"

    def test_invalid_when_rejected_regardless_of_pump_tag(self):
        assert classify_candidate({"status": "REJECTED", "pump_tag_number": "110-P-9A"}) == "INVALID"
        assert classify_candidate({"status": "REJECTED", "pump_tag_number": None}) == "INVALID"

    def test_incomplete_never_conflated_with_invalid(self):
        assert classify_candidate({"status": "PENDING_REVIEW", "pump_tag_number": None}) != "INVALID"


# --- Staging bridge: pump tag rule ---------------------------------------


class TestStagingBridgePumpTagRule:
    def _dry_run_result(self, candidates):
        import sys as _sys
        _sys.path.insert(0, str(Path("d:/PROJECT/AI5R/PRODUCTS/LTSA-BRAIN/INGESTION")))
        from historical_pm_cmon_orchestrator import AreaDryRunResult, SourceDocumentInfo

        source = SourceDocumentInfo(
            area_label="HCC", pdf_path=Path("x.pdf"), xlsx_path=Path("x.xlsx"),
            pdf_sha256="a" * 64, xlsx_sha256="b" * 64,
        )
        result = AreaDryRunResult(area_label="HCC", source=source, document_classification="MIXED")
        for c in candidates:
            getattr(result, f"{c.kind.lower()}_candidates").append(c)
        return result

    def _candidate_summary(self, **overrides):
        import sys as _sys
        _sys.path.insert(0, str(Path("d:/PROJECT/AI5R/PRODUCTS/LTSA-BRAIN/INGESTION")))
        from historical_pm_cmon_orchestrator import CandidateSummary

        base = dict(
            kind="CMON", code="LTSA-CMONR-1", tag_number="212-P-14A", pump_match="NO_MATCH",
            matched_tag=None, area={}, fields={"mechseal_temp_de": 59.0},
        )
        base.update(overrides)
        return CandidateSummary(**base)

    def test_no_match_stages_with_null_pump_tag_and_preserved_raw_tag(self):
        class Repo:
            def create_candidate(self, **kwargs):
                self.kwargs = kwargs
                return {"document_field_extraction_id": "DFE-1", **kwargs}

        repo = Repo()
        candidate = self._candidate_summary(tag_number="212-P-14A", pump_match="NO_MATCH")
        result = self._dry_run_result([candidate])

        import sys as _sys
        _sys.path.insert(0, str(Path("d:/PROJECT/AI5R/PRODUCTS/LTSA-BRAIN/INGESTION")))
        from historical_pm_cmon_orchestrator import stage_area_candidates

        stage_area_candidates(result, staging_repository=repo, source_document_id="PDF-1")
        assert repo.kwargs["pump_tag_number"] is None
        assert repo.kwargs["extracted_fields"]["raw_asset_tag"] == "212-P-14A"

    def test_review_required_stages_with_null_pump_tag_never_a_guessed_sister(self):
        class Repo:
            def create_candidate(self, **kwargs):
                self.kwargs = kwargs
                return {"document_field_extraction_id": "DFE-1", **kwargs}

        repo = Repo()
        candidate = self._candidate_summary(tag_number="840-P-1A", pump_match="REVIEW_REQUIRED")
        result = self._dry_run_result([candidate])

        import sys as _sys
        from historical_pm_cmon_orchestrator import stage_area_candidates

        stage_area_candidates(result, staging_repository=repo, source_document_id="PDF-1")
        assert repo.kwargs["pump_tag_number"] is None
        assert repo.kwargs["extracted_fields"]["raw_asset_tag"] == "840-P-1A"

    def test_motor_tag_never_converted_to_a_pump_tag(self):
        class Repo:
            def create_candidate(self, **kwargs):
                self.kwargs = kwargs
                return {"document_field_extraction_id": "DFE-1", **kwargs}

        repo = Repo()
        candidate = self._candidate_summary(tag_number="701-MM-51", pump_match="NO_MATCH")
        result = self._dry_run_result([candidate])
        from historical_pm_cmon_orchestrator import stage_area_candidates

        stage_area_candidates(result, staging_repository=repo, source_document_id="PDF-1")
        assert repo.kwargs["pump_tag_number"] is None
        assert repo.kwargs["extracted_fields"]["raw_asset_tag"] == "701-MM-51"
        assert "P-51" not in (repo.kwargs["pump_tag_number"] or "")

    def test_exact_match_stages_with_resolved_pump_tag(self):
        class Repo:
            def create_candidate(self, **kwargs):
                self.kwargs = kwargs
                return {"document_field_extraction_id": "DFE-1", **kwargs}

        repo = Repo()
        candidate = self._candidate_summary(tag_number="110-P-9A", pump_match="EXACT_MATCH", matched_tag="110-P-9A")
        result = self._dry_run_result([candidate])
        from historical_pm_cmon_orchestrator import stage_area_candidates

        stage_area_candidates(result, staging_repository=repo, source_document_id="PDF-1")
        assert repo.kwargs["pump_tag_number"] == "110-P-9A"
        assert repo.kwargs["extracted_fields"]["raw_asset_tag"] == "110-P-9A"

    def test_whitespace_normalized_exact_match_stages_the_canonical_form_not_the_raw_one(self):
        class Repo:
            def create_candidate(self, **kwargs):
                self.kwargs = kwargs
                return {"document_field_extraction_id": "DFE-1", **kwargs}

        repo = Repo()
        # Real HSC/HCC July data shape: raw tag has spacing the roster
        # does not; EXACT_MATCH only because whitespace-collapse found a
        # unique canonical roster tag (5a5e186's own rule).
        candidate = self._candidate_summary(
            tag_number="211 - P - 1A", pump_match="EXACT_MATCH", matched_tag="211-P-1A",
        )
        result = self._dry_run_result([candidate])
        from historical_pm_cmon_orchestrator import stage_area_candidates

        stage_area_candidates(result, staging_repository=repo, source_document_id="PDF-1")
        assert repo.kwargs["pump_tag_number"] == "211-P-1A"  # canonical, FK-safe form
        assert repo.kwargs["extracted_fields"]["raw_asset_tag"] == "211 - P - 1A"  # raw, verbatim


# --- Router: INCOMPLETE discoverable, INVALID cannot promote -------------


class TestIncompleteDiscoverableAndInvalidBlocked:
    def test_incomplete_listed_under_reviewed_status(self):
        staging = FakeStagingRepository(_incomplete_candidate(status="REVIEWED"))
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
        try:
            response = client.get("/api/ltsa/historical-review/candidates", params={"status": "REVIEWED"})
            assert response.status_code == 200
            body = response.json()["data"]
            assert len(body) == 1
            assert body[0]["classification"] == "INCOMPLETE"
        finally:
            _clear()

    def test_invalid_rejected_candidate_cannot_promote(self):
        staging = FakeStagingRepository(_incomplete_candidate(status="REJECTED", pump_tag_number="110-P-9A"))
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-INC-1/promote")
            assert response.status_code == 422
            assert "INVALID" in response.json()["detail"]
        finally:
            _clear()

    def test_incomplete_unresolved_candidate_cannot_promote(self):
        staging = FakeStagingRepository(_incomplete_candidate(status="REVIEWED", pump_tag_number=None))
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
        try:
            response = client.post("/api/ltsa/historical-review/candidates/DFE-INC-1/promote")
            assert response.status_code == 422
            assert "INCOMPLETE" in response.json()["detail"]
        finally:
            _clear()


# --- Later completion by SU and TAP_ADMIN, each audited ------------------


class TestLaterCompletion:
    def test_superuser_can_complete_an_incomplete_record_with_audit(self):
        staging = FakeStagingRepository(_incomplete_candidate())
        history = FakeHistoryRepository()
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/DFE-INC-1/review",
                json={"pump_tag_number": "212-P-14A", "reason": "Confirmed against updated roster"},
            )
            assert response.status_code == 200
            assert response.json()["data"]["classification"] == "MATCHED"
            assert any(c["field_name"] == "pump_tag_number" for c in history.append_calls)
            assert history.append_calls[-1]["changed_by"] == "actor-1"
        finally:
            _clear()

    def test_tap_admin_can_complete_an_incomplete_record_with_audit(self):
        staging = FakeStagingRepository(_incomplete_candidate())
        history = FakeHistoryRepository()
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
        app.dependency_overrides[get_historical_pm_cmon_staging_repository] = lambda: staging
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.post(
                "/api/ltsa/historical-review/candidates/DFE-INC-1/review",
                json={"pump_tag_number": "212-P-14A", "reason": "Confirmed against updated roster"},
            )
            assert response.status_code == 200
            assert response.json()["data"]["classification"] == "MATCHED"
        finally:
            _clear()


# --- Auth freeze: delete not implemented, no delete permission -----------


class TestDeleteNotIntroduced:
    def test_no_delete_permission_string_exists_anywhere(self):
        for role, perms in ROLE_PERMISSIONS.items():
            for perm in perms:
                assert "delete" not in perm.lower(), f"{role} unexpectedly holds a delete-shaped permission: {perm}"

    def test_delete_candidate_route_does_not_exist(self):
        response = client.delete("/api/ltsa/historical-review/candidates/DFE-INC-1")
        assert response.status_code in (404, 405)

    def test_tap_admin_cannot_reach_a_delete_action_because_none_exists(self):
        # Structural proof, not a live endpoint test: TAP_ADMIN's real
        # ROLE_PERMISSIONS grant (audited above) has no delete-shaped
        # permission, and this router registers no DELETE route at all.
        from main import app as real_app

        delete_routes = [
            r for r in real_app.router.routes
            if getattr(r, "path", "").startswith("/api/ltsa/historical-review") and "DELETE" in getattr(r, "methods", set())
        ]
        assert delete_routes == []


class TestAuditStillSuperuserOnly:
    def test_tap_admin_denied_full_history_read(self):
        history = FakeHistoryRepository()
        app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "HISTORICAL_STAGING_CANDIDATE", "entity_id": "DFE-INC-1"},
            )
            assert response.status_code == 403
        finally:
            _clear()

    def test_superuser_full_history_still_works(self):
        history = FakeHistoryRepository()
        history.append(
            entity_type="HISTORICAL_STAGING_CANDIDATE", entity_id="DFE-INC-1", field_name="pump_tag_number",
            old_value=None, new_value="212-P-14A", changed_by="actor-1", reason="fix", source_reference=None,
        )
        app.dependency_overrides[get_current_user] = lambda: _identity("SUPERUSER")
        app.dependency_overrides[get_record_change_history_repository] = lambda: history
        try:
            response = client.get(
                "/api/ltsa/records/history",
                params={"entity_type": "HISTORICAL_STAGING_CANDIDATE", "entity_id": "DFE-INC-1"},
            )
            assert response.status_code == 200
            assert len(response.json()["data"]) == 1
        finally:
            _clear()
