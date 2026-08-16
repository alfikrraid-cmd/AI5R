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
