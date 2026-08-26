"""MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- batch-submit/batch-
technical-review route tests, same FastAPI TestClient + dependency-
override discipline as test_pm_occurrence_write_router.py /
test_condition_monitoring_write_router.py."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_current_user,
    get_pm_occurrence_repository,
    get_condition_monitoring_reading_repository,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeRepository:
    """Mirrors the real repository's own None-on-ineligible / dict-on-
    success contract, without any DB -- exactly what submit()/
    technical_finalize()/technical_return_for_correction() already return."""

    def __init__(self, *, draft_codes=(), submitted_codes=()):
        self.draft_codes = set(draft_codes)
        self.submitted_codes = set(submitted_codes)
        self.calls: list[tuple] = []

    def submit(self, code, **kwargs):
        self.calls.append(("submit", code, kwargs))
        if code not in self.draft_codes:
            return None
        self.draft_codes.discard(code)
        self.submitted_codes.add(code)
        return {"code": code, "workflow_status": "SUBMITTED", **kwargs}

    def technical_finalize(self, code, **kwargs):
        self.calls.append(("technical_finalize", code, kwargs))
        if code not in self.submitted_codes:
            return None
        self.submitted_codes.discard(code)
        return {"code": code, "workflow_status": "FINALIZED", **kwargs}

    def technical_return_for_correction(self, code, **kwargs):
        self.calls.append(("technical_return_for_correction", code, kwargs))
        if code not in self.submitted_codes:
            return None
        self.submitted_codes.discard(code)
        return {"code": code, "workflow_status": "RETURNED_FOR_CORRECTION", **kwargs}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role, repository_dependency, *, user_id="actor-1", repository=None):
    fake = repository if repository is not None else FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[repository_dependency] = lambda: fake
    return fake


PM_URL = "/api/ltsa/pm-occurrences"
CMON_URL = "/api/ltsa/condition-monitoring-readings"


@pytest.mark.parametrize("base_url,repo_dep", [(PM_URL, get_pm_occurrence_repository), (CMON_URL, get_condition_monitoring_reading_repository)])
class TestBatchReview:
    # A/B -- only eligible records transition; ineligible ones are
    # reported skipped, never succeeded.
    def test_batch_submit_only_accepts_eligible_draft_records(self, base_url, repo_dep):
        fake = _override("TAP_ENGINEER", repo_dep, repository=FakeRepository(draft_codes=["A", "B"]))
        response = client.post(f"{base_url}/batch-submit", json={"codes": ["A", "B", "C"]})
        assert response.status_code == 200
        data = response.json()["data"]
        assert sorted(data["succeeded"]) == ["A", "B"]
        assert [s["code"] for s in data["skipped"]] == ["C"]
        assert data["failed"] == []
        assert fake.submitted_codes == {"A", "B"}

    def test_batch_technical_review_only_accepts_eligible_submitted_records(self, base_url, repo_dep):
        fake = _override("JOHN_CRANE_ENGINEER", repo_dep, repository=FakeRepository(submitted_codes=["S1", "S2"]))
        response = client.post(f"{base_url}/batch-technical-review", json={"codes": ["S1", "S2", "NOTSUBMITTED"], "action": "APPROVE"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert sorted(data["succeeded"]) == ["S1", "S2"]
        assert [s["code"] for s in data["skipped"]] == ["NOTSUBMITTED"]

    # C -- no direct DRAFT->FINALIZED path: a DRAFT-only code sent to
    # batch-technical-review is skipped, never finalized.
    def test_draft_cannot_jump_directly_to_finalized_via_batch_technical_review(self, base_url, repo_dep):
        fake = _override("JOHN_CRANE_ENGINEER", repo_dep, repository=FakeRepository(draft_codes=["D1"]))
        response = client.post(f"{base_url}/batch-technical-review", json={"codes": ["D1"], "action": "APPROVE"})
        data = response.json()["data"]
        assert data["succeeded"] == []
        assert data["skipped"][0]["code"] == "D1"
        assert fake.calls == [("technical_finalize", "D1", {"technical_reviewed_by": "actor-1", "technical_outcome": "TECHNICALLY_APPROVED", "technical_comment": None, "technical_recommendation": None})]

    # D -- the batch route calls the SAME repository method (by name and
    # kwargs shape) the individual route already calls -- no parallel
    # business logic.
    def test_batch_submit_calls_the_same_submit_method_individual_records_use(self, base_url, repo_dep):
        fake = _override("TAP_ENGINEER", repo_dep, repository=FakeRepository(draft_codes=["A"]))
        client.post(f"{base_url}/batch-submit", json={"codes": ["A"]})
        assert fake.calls == [("submit", "A", {"submitted_by": "actor-1"})]

    # E -- unauthorized role rejected, same RBAC gate as individual routes.
    def test_pertamina_engineer_cannot_batch_submit(self, base_url, repo_dep):
        _override("PERTAMINA_ENGINEER", repo_dep)
        response = client.post(f"{base_url}/batch-submit", json={"codes": ["A"]})
        assert response.status_code == 403

    def test_tap_engineer_cannot_batch_technical_review(self, base_url, repo_dep):
        _override("TAP_ENGINEER", repo_dep)
        response = client.post(f"{base_url}/batch-technical-review", json={"codes": ["A"], "action": "APPROVE"})
        assert response.status_code == 403

    # F -- actor is always the authenticated identity, never spoofable
    # via the request body (no submitted_by/technical_reviewed_by field
    # exists on BatchCodesRequest/BatchTechnicalReviewRequest at all).
    def test_actor_is_always_the_authenticated_identity(self, base_url, repo_dep):
        fake = _override("TAP_ENGINEER", repo_dep, user_id="real-actor", repository=FakeRepository(draft_codes=["A"]))
        client.post(f"{base_url}/batch-submit", json={"codes": ["A"], "submitted_by": "spoofed"})
        assert fake.calls[0][2]["submitted_by"] == "real-actor"

    # G -- truthful mixed results: never reports success for a record
    # that did not transition.
    def test_mixed_batch_reports_truthful_succeeded_and_skipped(self, base_url, repo_dep):
        _override("TAP_ENGINEER", repo_dep, repository=FakeRepository(draft_codes=["A"]))
        response = client.post(f"{base_url}/batch-submit", json={"codes": ["A", "MISSING"]})
        data = response.json()["data"]
        assert "MISSING" not in data["succeeded"]
        assert any(s["code"] == "MISSING" for s in data["skipped"])

    # H/I -- structural: the batch route's kwargs to submit()/
    # technical_finalize() never include provenance, source_reference, or
    # any engineering-data field -- only workflow-transition actor/action
    # fields, same as the individual routes.
    def test_batch_submit_never_passes_provenance_or_engineering_fields(self, base_url, repo_dep):
        fake = _override("TAP_ENGINEER", repo_dep, repository=FakeRepository(draft_codes=["A"]))
        client.post(f"{base_url}/batch-submit", json={"codes": ["A"]})
        kwargs = fake.calls[0][2]
        assert set(kwargs) == {"submitted_by"}
