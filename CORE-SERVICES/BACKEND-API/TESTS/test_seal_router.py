import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import (
    get_current_user,
    get_seal_gateway,
    get_seal_master_data_repository,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)

# MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser", email="test-superuser@tap.internal",
    organization_id="test-org-tap", organization_code="TAP",
    role="TAP_ADMIN", permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)



# MWO-LTSA-041 -- Mechanical Seal Workspace Integration. Router only: no
# filtering, no derivation, no business logic here -- each Gateway's own
# list_*() result is returned unchanged, mirroring pumps.py's
# list_ltsa_pumps pass-through exactly. Reuses SealGateway/SealStockGateway/
# SealPumpCompatibilityGateway unmodified -- no new gateway, service, or
# repository layer.


class FakeSealGateway:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def list_seals(self):
        self.calls += 1
        return self.response


class FakeSealStockGateway:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def list_seal_stocks(self):
        self.calls += 1
        return self.response


class FakeSealPumpCompatibilityGateway:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def list_seal_pump_compatibilities(self):
        self.calls += 1
        return self.response


def _response(data):
    return {"success": True, "message": "ok", "count": len(data), "data": data}


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    # MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


def test_seals_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seals" in paths


def test_seal_stock_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seal-stock" in paths


def test_seal_compatibility_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seal-compatibility" in paths


def test_all_three_routes_allow_only_get():
    openapi = client.get("/openapi.json").json()["paths"]
    for path in ("/api/ltsa/seals", "/api/ltsa/seal-stock", "/api/ltsa/seal-compatibility"):
        assert set(openapi[path]) == {"get"}


def test_get_seals_returns_the_gateways_response_unchanged():
    fake = FakeSealGateway(_response([{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}]))
    app.dependency_overrides[get_seal_gateway] = lambda: fake

    response = client.get("/api/ltsa/seals")

    assert response.status_code == 200
    assert response.json() == fake.response
    assert fake.calls == 1


def test_get_seal_stock_returns_the_gateways_response_unchanged():
    fake = FakeSealStockGateway(_response([{"seal_code": "SC-001", "quantity_on_hand": 4}]))
    app.dependency_overrides[get_seal_stock_gateway] = lambda: fake

    response = client.get("/api/ltsa/seal-stock")

    assert response.status_code == 200
    assert response.json() == fake.response
    assert fake.calls == 1


def test_get_seal_compatibility_returns_the_gateways_response_unchanged():
    fake = FakeSealPumpCompatibilityGateway(
        _response([{"seal_code": "SC-001", "pump_tag_number": "211-P-1A"}])
    )
    app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: fake

    response = client.get("/api/ltsa/seal-compatibility")

    assert response.status_code == 200
    assert response.json() == fake.response
    assert fake.calls == 1


def test_get_seals_propagates_a_failure_response_unchanged():
    fake = FakeSealGateway({"success": False, "message": "n8n unreachable"})
    app.dependency_overrides[get_seal_gateway] = lambda: fake

    response = client.get("/api/ltsa/seals")

    assert response.status_code == 200
    assert response.json()["success"] is False


# --- MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- PATCH /api/ltsa/seals/{seal_code} ---


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeSealMasterDataRepository:
    def __init__(self, *, existing_seals=None):
        self.existing_seals = existing_seals if existing_seals is not None else {"SC-001"}
        self.update_calls = []

    def update_seal_identifiers(self, seal_code, *, kimap_pertamina, gpn_john_crane, updated_by):
        self.update_calls.append(
            {"seal_code": seal_code, "kimap_pertamina": kimap_pertamina,
             "gpn_john_crane": gpn_john_crane, "updated_by": updated_by}
        )
        if seal_code not in self.existing_seals:
            return None
        return {
            "seal_code": seal_code, "kimap_pertamina": kimap_pertamina,
            "gpn_john_crane": gpn_john_crane, "created_by": None,
            "updated_by": updated_by, "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-08-17T00:00:00",
        }


def test_patch_seal_identifiers_route_is_registered_patch_only():
    openapi = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seals/{seal_code}" in openapi
    assert set(openapi["/api/ltsa/seals/{seal_code}"]) == {"patch"}


def test_authorized_roles_can_update_seal_identifiers():
    # master.edit's real, current grant (auth_service.ROLE_PERMISSIONS) is
    # SUPERUSER + TAP_ADMIN only -- TAP_ENGINEER is NOT in that set today
    # (confirmed by reading the real dict, not assumed). Phase 6's own
    # conditional ("TAP_ENGINEER: manual completion only if existing
    # master.edit policy safely permits it") is therefore satisfied by
    # TAP_ENGINEER staying read-only here -- see the dedicated denial test
    # below for that boundary, proven rather than asserted.
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake = FakeSealMasterDataRepository()
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_seal_master_data_repository] = lambda fake=fake: fake

        response = client.patch(
            "/api/ltsa/seals/SC-001",
            json={"kimap_pertamina": "KIMAP-0001", "gpn_john_crane": "GPN-JC-9001"},
        )

        assert response.status_code == 200, f"{role} should be authorized"
        assert response.json()["data"]["kimap_pertamina"] == "KIMAP-0001"


def test_tap_engineer_cannot_update_seal_identifiers_today():
    # master.edit does not grant to TAP_ENGINEER in the current, real
    # ROLE_PERMISSIONS matrix -- Phase 6 explicitly allows this outcome
    # (reuse the existing policy as-is rather than widen it to fit the
    # UI). Disclosed in the completion report as the smallest-architecture
    # choice, not an oversight.
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch("/api/ltsa/seals/SC-001", json={"kimap_pertamina": "KIMAP-0001"})

    assert response.status_code == 403
    assert fake.update_calls == []


def test_john_crane_engineer_cannot_update_seal_identifiers():
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("JOHN_CRANE_ENGINEER")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch("/api/ltsa/seals/SC-001", json={"kimap_pertamina": "KIMAP-0001"})

    assert response.status_code == 403
    assert fake.update_calls == []


def test_pertamina_engineer_cannot_update_seal_identifiers():
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("PERTAMINA_ENGINEER")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch("/api/ltsa/seals/SC-001", json={"kimap_pertamina": "KIMAP-0001"})

    assert response.status_code == 403
    assert fake.update_calls == []


def test_pertamina_viewer_cannot_update_seal_identifiers():
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("PERTAMINA_VIEWER")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch("/api/ltsa/seals/SC-001", json={"kimap_pertamina": "KIMAP-0001"})

    assert response.status_code == 403
    assert fake.update_calls == []


def test_updated_by_is_always_the_authenticated_actor_never_the_request_body():
    # Phase 18: client cannot spoof updated_by -- SealIdentifierUpdateRequest
    # has no such field at all, so a client attempting to smuggle one into
    # the JSON body is silently ignored by pydantic (extra field, dropped),
    # never forwarded to the repository.
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch(
        "/api/ltsa/seals/SC-001",
        json={"kimap_pertamina": "KIMAP-0001", "updated_by": "spoofed-actor"},
    )

    assert response.status_code == 200
    assert fake.update_calls[0]["updated_by"] == "real-actor"


def test_patch_returns_404_for_a_seal_that_does_not_exist():
    fake = FakeSealMasterDataRepository(existing_seals=set())
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch("/api/ltsa/seals/SC-MISSING", json={"kimap_pertamina": "KIMAP-0001"})

    assert response.status_code == 404


def test_patch_never_accepts_a_quantity_field():
    # Phase 10 -- stock quantity is not reachable through this endpoint at
    # all; the request model has no such field, so it is silently dropped
    # by pydantic, never reaching the repository call.
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch(
        "/api/ltsa/seals/SC-001",
        json={"kimap_pertamina": "KIMAP-0001", "quantity_on_hand": 999},
    )

    assert response.status_code == 200
    assert "quantity_on_hand" not in fake.update_calls[0]


def test_empty_string_identifier_is_normalized_to_none_before_reaching_the_repository():
    fake = FakeSealMasterDataRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    app.dependency_overrides[get_seal_master_data_repository] = lambda: fake

    response = client.patch(
        "/api/ltsa/seals/SC-001",
        json={"kimap_pertamina": "", "gpn_john_crane": "  "},
    )

    assert response.status_code == 200
    assert fake.update_calls[0]["kimap_pertamina"] is None
    assert fake.update_calls[0]["gpn_john_crane"] is None
