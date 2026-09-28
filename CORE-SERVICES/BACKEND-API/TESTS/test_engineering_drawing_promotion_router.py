"""MWO-LTSA-DRAWING-INPUT-R5D.2 -- engineering_drawing router's new
promotion endpoint: RBAC (maintenance.admin_review, not maintenance.write/
drawing.read), HTTP error mapping for every bounded promotion-service
exception, actor/scope non-forgeability, response allowlisting, and
service-call-count proof. Same REAL-app TestClient convention as
test_engineering_drawing_router.py -- the frozen
EngineeringDrawingPromotionService itself is NEVER exercised here (that is
test_engineering_drawing_promotion_service.py's own job against real
Postgres); this file mocks the service at the router boundary to test HTTP
mapping only, per this MWO's own explicit instruction.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user, get_engineering_drawing_promotion_service  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.engineering_drawing_promotion_service import (  # noqa: E402
    AlreadyPromoted,
    CandidateNotEligible,
    CandidateNotFound,
    CandidateRejected,
    CanonicalConflict,
    DrawingMatchRequiresReview,
    InvalidReviewPayload,
    PromotionConcurrencyConflict,
    ReferenceNotFound,
    RevisionMatchRequiresReview,
    ScopeDenied,
)

client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, user_id="actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


_SUCCESS_RESULT = {
    "candidate_id": "DFE-1", "promotion_status": "PROMOTED", "drawing_code": "D-NEW",
    "drawing_match": "NEW_DRAWING", "revision_code": "R-NEW", "revision_match": "NEW_REVISION",
    "artifact_codes": ["A-NEW"], "attribute_codes": [], "bom_line_codes": [], "link_codes": [],
    "warnings": [], "conflicts": [], "idempotent_replay": False,
}


class FakePromotionService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._raise: Exception | None = None
        self._result = dict(_SUCCESS_RESULT)

    def promote_candidate(self, candidate_id, *, promoted_by, actor_scope=None):
        self.calls.append((candidate_id, promoted_by, actor_scope))
        if self._raise:
            raise self._raise
        return {**self._result, "candidate_id": candidate_id}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, *, service=None, **identity_kwargs):
    fake = service if service is not None else FakePromotionService()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, **identity_kwargs)
    app.dependency_overrides[get_engineering_drawing_promotion_service] = lambda: fake
    return fake


def _promote(candidate_id="DFE-1", **kwargs):
    return client.post(f"/api/ltsa/engineering-drawings/promotions/{candidate_id}", **kwargs)


# ---- 01: success ----

def test_01_success_returns_bounded_response():
    fake = _override("TAP_ADMIN")
    response = _promote()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {**_SUCCESS_RESULT, "candidate_id": "DFE-1"}


# ---- 02-12: bounded exception -> HTTP mapping ----

def test_02_candidate_not_found_404():
    fake = _override("TAP_ADMIN")
    fake._raise = CandidateNotFound("DFE-MISSING")
    response = _promote("DFE-MISSING")
    assert response.status_code == 404


def test_03_candidate_not_eligible_409():
    fake = _override("TAP_ADMIN")
    fake._raise = CandidateNotEligible("not eligible")
    response = _promote()
    assert response.status_code == 409


def test_04_candidate_rejected_409():
    fake = _override("TAP_ADMIN")
    fake._raise = CandidateRejected("rejected")
    response = _promote()
    assert response.status_code == 409


def test_05_invalid_review_payload_422():
    fake = _override("TAP_ADMIN")
    fake._raise = InvalidReviewPayload("bad payload")
    response = _promote()
    assert response.status_code == 422


def test_06_drawing_match_requires_review_409():
    fake = _override("TAP_ADMIN")
    fake._raise = DrawingMatchRequiresReview("ambiguous")
    response = _promote()
    assert response.status_code == 409


def test_07_revision_match_requires_review_409():
    fake = _override("TAP_ADMIN")
    fake._raise = RevisionMatchRequiresReview("ambiguous")
    response = _promote()
    assert response.status_code == 409


def test_08_canonical_conflict_409():
    fake = _override("TAP_ADMIN")
    fake._raise = CanonicalConflict("collision")
    response = _promote()
    assert response.status_code == 409


def test_09_reference_not_found_422():
    fake = _override("TAP_ADMIN")
    fake._raise = ReferenceNotFound("ASSET:X missing")
    response = _promote()
    assert response.status_code == 422


def test_10_scope_denied_403():
    fake = _override("TAP_ADMIN")
    fake._raise = ScopeDenied("out of scope")
    response = _promote()
    assert response.status_code == 403


def test_11_already_promoted_returns_200_idempotent():
    fake = _override("TAP_ADMIN")
    already_result = {**_SUCCESS_RESULT, "promotion_status": "ALREADY_PROMOTED", "idempotent_replay": True}
    fake._raise = AlreadyPromoted("DFE-1", already_result)
    response = _promote()
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["idempotent_replay"] is True
    assert body["data"]["promotion_status"] == "ALREADY_PROMOTED"


def test_12_promotion_concurrency_conflict_409():
    fake = _override("TAP_ADMIN")
    fake._raise = PromotionConcurrencyConflict("race")
    response = _promote()
    assert response.status_code == 409


# ---- 13-16: RBAC ----

def test_13_maintenance_admin_review_allowed():
    _override("TAP_ADMIN")
    response = _promote()
    assert response.status_code == 200


def test_14_maintenance_write_without_admin_review_denied():
    fake = _override("TAP_ENGINEER")  # has maintenance.write, not maintenance.admin_review
    response = _promote()
    assert response.status_code == 403
    assert fake.calls == []


def test_15_drawing_read_only_denied():
    fake = _override("PERTAMINA_ENGINEER")  # has drawing.read only
    response = _promote()
    assert response.status_code == 403
    assert fake.calls == []


def test_16_unauthenticated_denied():
    # Deliberately do not override get_current_user -- the real dependency
    # sees no Authorization header and raises 401 itself.
    app.dependency_overrides[get_engineering_drawing_promotion_service] = lambda: FakePromotionService()
    response = _promote()
    assert response.status_code == 401


# ---- 17-20: no client-forgeable input ----

def test_17_candidate_id_path_forwarded_exactly():
    fake = _override("TAP_ADMIN")
    _promote("DFE-XYZ-123")
    assert fake.calls[0][0] == "DFE-XYZ-123"


def test_18_actor_identity_comes_from_dependency_not_body():
    fake = _override("TAP_ADMIN", user_id="real-actor-42")
    _promote()
    assert fake.calls[0][1] == "real-actor-42"


def test_19_scope_context_forwarded_correctly():
    # HONEST GAP: no role in ROLE_PERMISSIONS currently combines
    # maintenance.admin_review with an Area/MA-restricted data_scope --
    # both roles holding that permission (SUPERUSER, TAP_ADMIN) are in
    # auth_service.py's own _UNRESTRICTED_ROLES, so resolve_area_scope()
    # always returns None for every actor who can reach this endpoint at
    # all under the current role matrix. This test proves the router
    # forwards whatever resolve_area_scope() returns UNMODIFIED (the one
    # reachable case, None) rather than fabricating a scope of its own;
    # non-None forwarding for a hypothetical restricted admin-review actor
    # is not exercisable here without inventing a role/permission
    # combination that doesn't exist -- resolve_area_scope()'s own
    # frozenset-construction logic is separately covered by
    # API/TESTS/test_auth_service.py.
    fake = _override("TAP_ADMIN", data_scope_type="AREA", data_scope_value="HOC")
    _promote()
    assert fake.calls[0][2] is None


def test_20_no_client_actor_override_accepted():
    fake = _override("TAP_ADMIN", user_id="real-actor-42")
    response = client.post(
        "/api/ltsa/engineering-drawings/promotions/DFE-1",
        json={"promoted_by": "attacker-controlled", "actor_scope": ["FORGED"]},
    )
    assert response.status_code == 200
    assert fake.calls[0][1] == "real-actor-42"  # never "attacker-controlled"


# ---- 21-23: response allowlist ----

def test_21_no_raw_extracted_fields_in_response():
    _override("TAP_ADMIN")
    response = _promote()
    assert "extracted_fields" not in response.text


def test_22_no_reviewed_fields_in_response():
    _override("TAP_ADMIN")
    response = _promote()
    assert "reviewed_fields" not in response.text


def test_23_no_credentials_or_storage_path_in_response():
    _override("TAP_ADMIN")
    response = _promote()
    lowered = response.text.lower()
    for leak in ("password", "object_storage_key", "host=", "dbname"):
        assert leak not in lowered


# ---- 24-25: call-count proof ----

def test_24_service_called_exactly_once_on_success():
    fake = _override("TAP_ADMIN")
    _promote()
    assert len(fake.calls) == 1


def test_25_service_called_zero_times_when_permission_denied():
    fake = _override("PERTAMINA_ENGINEER")
    _promote()
    assert len(fake.calls) == 0


# ---- 26: unexpected exception follows existing bounded 500 policy ----

def test_26_unexpected_exception_returns_500_without_leaking_internals():
    fake = _override("TAP_ADMIN")
    fake._raise = RuntimeError("unexpected internal detail: secret=xyz")
    local_client = TestClient(app, raise_server_exceptions=False)
    response = local_client.post("/api/ltsa/engineering-drawings/promotions/DFE-1")
    assert response.status_code == 500
    assert "secret=xyz" not in response.text
