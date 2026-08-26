import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from API.auth_service import AuthenticatedIdentity, ROLE_PERMISSIONS
from dependencies import get_current_user, get_mechanical_seal_stock_repository
from main import app

client = TestClient(app)


class FakeStockRepository:
    def __init__(self):
        self.calls = []

    def list_pools(self, **kwargs):
        self.calls.append(kwargs)
        return {"success": True, "items": [], "data": [], "total": 0, "limit": kwargs["limit"], "offset": kwargs["offset"]}

    def get_pool(self, *_args, **_kwargs):
        return None


def identity(role):
    return AuthenticatedIdentity(
        user_id="u-1", email="u-1@example.test", organization_id="org-1",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
    )


def test_stock_list_is_paginated_and_gpn_visibility_is_server_side():
    repository = FakeStockRepository()
    app.dependency_overrides[get_current_user] = lambda: identity("PERTAMINA_ENGINEER")
    app.dependency_overrides[get_mechanical_seal_stock_repository] = lambda: repository
    try:
        response = client.get("/api/ltsa/mechanical-seal-stock?limit=25&offset=50&search=E12926")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repository.calls == [{
        "limit": 25, "offset": 50, "search": "E12926",
        "verification_status": None, "include_gpn": False,
    }]


def test_stock_list_allows_gpn_only_for_internal_roles():
    repository = FakeStockRepository()
    app.dependency_overrides[get_current_user] = lambda: identity("JOHN_CRANE_ENGINEER")
    app.dependency_overrides[get_mechanical_seal_stock_repository] = lambda: repository
    try:
        response = client.get("/api/ltsa/mechanical-seal-stock")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repository.calls[0]["include_gpn"] is True
