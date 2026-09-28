"""MWO-LTSA-DRAWING-INPUT-R4 -- engineering_drawing router tests: RBAC
(read/write/area-MA), 404/409 semantics, polymorphic validation
pass-through, retraction, no hard-delete route, artifact provenance
protection. Router IS wired into main.py this mission (dependencies.py/
main.py were clean at edit time) -- uses the REAL app (`from main import
app`), same convention as test_pm_occurrence_write_router.py, proving
real app registration rather than a standalone router-only app.
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
from dependencies import get_current_user, get_engineering_drawing_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.engineering_drawing_repository import (  # noqa: E402
    ComponentNotFound,
    CrossDrawingRevision,
    DuplicateActiveLink,
    DuplicatePrimaryArtifact,
    InvalidLinkTarget,
    KnowledgeSourceNotFound,
    RevisionNotFound,
)

client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, user_id="actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class FakeEngineeringDrawingRepository:
    def __init__(self):
        self.calls: list[tuple] = []
        self._raise: Exception | None = None
        self._drawings = {"D1": {"drawing_code": "D1", "title": "X"}}
        self._detail = {"drawing": self._drawings["D1"], "current_revision": None, "revisions": [], "artifacts_by_revision": {}, "bom_by_revision": {}, "links": []}
        self._in_scope = True

    def list_drawings(self, **kwargs):
        self.calls.append(("list_drawings", kwargs))
        return {"success": True, "data": [], "items": [], "count": 0, "total": 0, "limit": kwargs.get("limit", 25), "offset": kwargs.get("offset", 0)}

    def create_drawing(self, **kwargs):
        self.calls.append(("create_drawing", kwargs))
        return {"drawing_code": "D-NEW", **kwargs}

    def is_drawing_in_scope(self, drawing_code, scope):
        self.calls.append(("is_drawing_in_scope", drawing_code, scope))
        return self._in_scope

    def get_drawing_detail(self, drawing_code, **kwargs):
        self.calls.append(("get_drawing_detail", drawing_code, kwargs))
        return self._detail if drawing_code == "D1" else None

    def update_drawing(self, drawing_code, **kwargs):
        self.calls.append(("update_drawing", drawing_code, kwargs))
        if drawing_code != "D1":
            return None
        return {"drawing_code": drawing_code, **kwargs.get("values", {})}

    def set_current_revision(self, drawing_code, revision_code, **kwargs):
        self.calls.append(("set_current_revision", drawing_code, revision_code, kwargs))
        if self._raise:
            raise self._raise
        if drawing_code != "D1":
            return None
        return {"drawing_code": drawing_code, "current_revision_code": revision_code}

    def list_revisions_for_drawing(self, drawing_code):
        self.calls.append(("list_revisions_for_drawing", drawing_code))
        return [] if drawing_code == "D1" else None

    def create_revision(self, **kwargs):
        self.calls.append(("create_revision", kwargs))
        if self._raise:
            raise self._raise
        return {"revision_code": "R-NEW", **kwargs}

    def find_revision(self, revision_code):
        self.calls.append(("find_revision", revision_code))
        if revision_code == "R1":
            return {"revision_code": "R1", "drawing_code": "D1"}
        return None

    def update_revision(self, revision_code, **kwargs):
        self.calls.append(("update_revision", revision_code, kwargs))
        if self._raise:
            raise self._raise
        if revision_code != "R1":
            return None
        return {"revision_code": revision_code, **kwargs.get("values", {})}

    def list_artifacts_for_revision(self, revision_code):
        self.calls.append(("list_artifacts_for_revision", revision_code))
        return [] if revision_code == "R1" else None

    def create_artifact(self, **kwargs):
        self.calls.append(("create_artifact", kwargs))
        if self._raise:
            raise self._raise
        return {"artifact_code": "A-NEW", **kwargs}

    def find_artifact(self, artifact_code):
        self.calls.append(("find_artifact", artifact_code))
        if artifact_code == "A1":
            return {"artifact_code": "A1", "revision_code": "R1", "artifact_class": "DERIVED_CAD"}
        return None

    def update_artifact(self, artifact_code, **kwargs):
        self.calls.append(("update_artifact", artifact_code, kwargs))
        if self._raise:
            raise self._raise
        if artifact_code != "A1":
            return None
        return {"artifact_code": artifact_code, "artifact_class": "DERIVED_CAD", **kwargs.get("values", {})}

    def list_links_for_drawing(self, drawing_code, **kwargs):
        self.calls.append(("list_links_for_drawing", drawing_code, kwargs))
        return [] if drawing_code == "D1" else None

    def create_link(self, **kwargs):
        self.calls.append(("create_link", kwargs))
        if self._raise:
            raise self._raise
        return {"link_code": "L-NEW", **kwargs}

    def retract_link(self, link_code, **kwargs):
        self.calls.append(("retract_link", link_code, kwargs))
        if link_code != "L1":
            return None
        return {"link_code": link_code, "retracted_at": "2026-01-01T00:00:00", **kwargs}

    def list_bom_for_revision(self, revision_code):
        self.calls.append(("list_bom_for_revision", revision_code))
        return [] if revision_code == "R1" else None

    def create_bom_line(self, **kwargs):
        self.calls.append(("create_bom_line", kwargs))
        if self._raise:
            raise self._raise
        return {"bom_line_code": "BOM-NEW", **kwargs}

    def find_bom_line(self, bom_line_code):
        self.calls.append(("find_bom_line", bom_line_code))
        if bom_line_code == "BOM1":
            return {"bom_line_code": "BOM1", "revision_code": "R1"}
        return None

    def update_bom_line(self, bom_line_code, **kwargs):
        self.calls.append(("update_bom_line", bom_line_code, kwargs))
        if self._raise:
            raise self._raise
        if bom_line_code != "BOM1":
            return None
        return {"bom_line_code": bom_line_code, **kwargs.get("values", {})}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, *, repository=None, **identity_kwargs):
    fake = repository or FakeEngineeringDrawingRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, **identity_kwargs)
    app.dependency_overrides[get_engineering_drawing_repository] = lambda: fake
    return fake


# ---- RBAC read ----

def test_role_without_drawing_read_denied_list():
    _override("PERTAMINA_VIEWER")  # no drawing.read
    response = client.get("/api/ltsa/engineering-drawings")
    assert response.status_code == 403


def test_role_with_drawing_read_allowed_list():
    _override("PERTAMINA_ENGINEER")
    response = client.get("/api/ltsa/engineering-drawings")
    assert response.status_code == 200


# ---- RBAC write ----

def test_role_without_maintenance_write_denied_create():
    _override("PERTAMINA_ENGINEER")  # drawing.read yes, maintenance.write no
    response = client.post("/api/ltsa/engineering-drawings", json={"title": "X"})
    assert response.status_code == 403


def test_role_with_maintenance_write_allowed_create():
    _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/engineering-drawings", json={"title": "X"})
    assert response.status_code == 200
    assert response.json()["data"]["drawing_code"] == "D-NEW"


# ---- 404 semantics ----

def test_get_drawing_not_found():
    fake = FakeEngineeringDrawingRepository()
    fake._in_scope = True
    _override("TAP_ENGINEER", repository=fake)
    response = client.get("/api/ltsa/engineering-drawings/D-MISSING")
    assert response.status_code == 404


def test_get_drawing_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/engineering-drawings/D1")
    assert response.status_code == 200
    assert response.json()["data"]["drawing"]["drawing_code"] == "D1"


def test_get_revision_not_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/engineering-drawing-revisions/R-MISSING")
    assert response.status_code == 404


def test_get_artifact_not_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/engineering-drawing-artifacts/A-MISSING")
    assert response.status_code == 404


def test_get_bom_line_not_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/engineering-drawing-bom/BOM-MISSING")
    assert response.status_code == 404


# ---- 409 semantics ----

def test_cross_drawing_current_revision_returns_409():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = CrossDrawingRevision("cross drawing")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post("/api/ltsa/engineering-drawings/D1/current-revision/R1")
    assert response.status_code == 409


def test_duplicate_active_link_returns_409():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = DuplicateActiveLink("dup")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/engineering-drawings/D1/links",
        json={"target_type": "ASSET", "target_code": "211-P-13AR", "relationship_type": "APPLIES_TO"},
    )
    assert response.status_code == 409


def test_duplicate_primary_artifact_returns_409():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = DuplicatePrimaryArtifact("dup")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/engineering-drawing-revisions/R1/artifacts",
        json={"knowledge_source_id": "KS-1", "artifact_class": "DERIVED_CAD", "is_primary": True},
    )
    assert response.status_code == 409


# ---- polymorphic validation pass-through ----

def test_invalid_link_target_returns_404():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = InvalidLinkTarget("bad target")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/engineering-drawings/D1/links",
        json={"target_type": "ASSET", "target_code": "NO-SUCH", "relationship_type": "APPLIES_TO"},
    )
    assert response.status_code == 404


def test_component_not_found_returns_404():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = ComponentNotFound("bad component")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post("/api/ltsa/engineering-drawing-revisions/R1/bom", json={"component_id": "NO-SUCH"})
    assert response.status_code == 404


def test_knowledge_source_not_found_returns_404():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = KnowledgeSourceNotFound("bad ks")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post("/api/ltsa/engineering-drawing-revisions/R1/artifacts", json={"knowledge_source_id": "NO-SUCH"})
    assert response.status_code == 404


def test_revision_not_found_returns_404():
    fake = FakeEngineeringDrawingRepository()
    fake._raise = RevisionNotFound("bad rev")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post("/api/ltsa/engineering-drawings/D1/revisions", json={"supersedes_revision_code": "NO-SUCH"})
    assert response.status_code == 404


# ---- area/MA scope ----

def test_area_restricted_identity_cannot_see_drawing_outside_scope():
    fake = FakeEngineeringDrawingRepository()
    fake._in_scope = False
    _override("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA1", repository=fake)
    response = client.get("/api/ltsa/engineering-drawings/D1")
    assert response.status_code == 404


def test_area_restricted_identity_can_see_drawing_inside_scope():
    fake = FakeEngineeringDrawingRepository()
    fake._in_scope = True
    _override("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA1", repository=fake)
    response = client.get("/api/ltsa/engineering-drawings/D1")
    assert response.status_code == 200


# ---- retraction / no hard delete ----

def test_retract_link():
    _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/engineering-drawing-links/L1/retract")
    assert response.status_code == 200
    assert response.json()["data"]["retracted_at"] is not None


def test_retract_link_not_found():
    _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/engineering-drawing-links/L-MISSING/retract")
    assert response.status_code == 404


def test_no_hard_delete_route_exists():
    _override("SUPERUSER")
    for path in (
        "/api/ltsa/engineering-drawings/D1",
        "/api/ltsa/engineering-drawing-revisions/R1",
        "/api/ltsa/engineering-drawing-artifacts/A1",
        "/api/ltsa/engineering-drawing-links/L1",
        "/api/ltsa/engineering-drawing-bom/BOM1",
    ):
        response = client.delete(path)
        assert response.status_code in (404, 405)


# ---- artifact provenance protection ----

def test_artifact_class_change_attempt_ignored_by_router():
    _override("TAP_ENGINEER")
    response = client.patch(
        "/api/ltsa/engineering-drawing-artifacts/A1",
        json={"artifact_class": "SOURCE_CAD", "verification_status": "VERIFIED"},
    )
    assert response.status_code == 200
    # Router forwards whatever the repository returns; the FIX lives in
    # the repository's own _ARTIFACT_UPDATABLE allowlist (proven directly
    # in test_engineering_drawing_repository.py::test_artifact_class_immutable_through_update).
    # Here we only prove the router does not itself special-case or
    # reject the field -- it passes model_dump(exclude_unset=True)
    # through unchanged, exactly like every other update route.
    assert response.json()["data"]["artifact_class"] == "DERIVED_CAD"


# ---- actor is server-controlled ----

def test_create_drawing_actor_is_server_controlled():
    fake = FakeEngineeringDrawingRepository()
    _override("TAP_ENGINEER", repository=fake, user_id="real-actor")
    client.post("/api/ltsa/engineering-drawings", json={"title": "X"})
    _, kwargs = fake.calls[-1]
    assert kwargs["created_by"] == "real-actor"
