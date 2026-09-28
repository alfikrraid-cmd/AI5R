import base64
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import dependencies  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.bi_dataset_service import BiSourceUnavailable, BiTableLimitExceeded  # noqa: E402
from API.bi_machine_auth_service import hash_secret  # noqa: E402
from API.bi_machine_credential_repository import InMemoryBiMachineCredentialRepository  # noqa: E402
from dependencies import get_bi_dataset_service, get_current_user  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
ENDPOINTS = ["metadata", "assets", "areas", "cm", "pm", "installations", "mtbf-intervals", "pump-current"]


def identity(role):
    return AuthenticatedIdentity(
        user_id="u-1", email="u-1@example.test", organization_id="org-1",
        organization_code="TAP", role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeService:
    def __init__(self, error=None):
        self.error = error

    def _table(self, name):
        if self.error:
            raise self.error
        return {"success": True, "contract_version": "ltsa-bi/1.0.0", "table": name, "row_count": 0, "data": []}

    def __getattr__(self, name):
        return lambda: self._table(name)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def serve(role=None, service=None):
    if role:
        app.dependency_overrides[get_current_user] = lambda: identity(role)
    app.dependency_overrides[get_bi_dataset_service] = lambda: service or FakeService()


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert body == {"success": False, "error_code": code, "message": body["message"], "contract_version": "ltsa-bi/1.0.0"}
    return body


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_unauthenticated_is_401_bi_envelope(endpoint):
    serve()
    assert_error(client.get(f"/api/ltsa/bi/v1/{endpoint}"), 401, "BI_UNAUTHENTICATED")


@pytest.mark.parametrize("role", ["PERTAMINA_VIEWER", "TAP_ENGINEER", "TAP_ADMIN", "JOHN_CRANE_ENGINEER"])
def test_roles_without_bi_read_are_403(role):
    serve(role)
    assert_error(client.get("/api/ltsa/bi/v1/cm"), 403, "BI_FORBIDDEN")


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_bi_reader_reads_every_bi_endpoint(endpoint):
    serve("BI_READER")
    response = client.get(f"/api/ltsa/bi/v1/{endpoint}")
    assert response.status_code == 200 and response.json()["contract_version"] == "ltsa-bi/1.0.0"


def test_superuser_may_verify_bi():
    serve("SUPERUSER")
    assert client.get("/api/ltsa/bi/v1/metadata").status_code == 200


def test_bi_reader_role_is_bi_read_only():
    assert ROLE_PERMISSIONS["BI_READER"] == frozenset({"bi.read"})
    assert "bi.read" in ROLE_PERMISSIONS["SUPERUSER"]
    assert all("bi.read" not in perms for role, perms in ROLE_PERMISSIONS.items() if role not in {"SUPERUSER", "BI_READER"})


def test_table_limit_is_413_without_data():
    serve("BI_READER", FakeService(BiTableLimitExceeded("cm has 50001 rows")))
    body = assert_error(client.get("/api/ltsa/bi/v1/cm"), 413, "BI_TABLE_LIMIT_EXCEEDED")
    assert "data" not in body


def test_source_unavailable_is_503():
    serve("BI_READER", FakeService(BiSourceUnavailable("source unavailable: pm_occurrence")))
    assert_error(client.get("/api/ltsa/bi/v1/pm"), 503, "BI_SOURCE_UNAVAILABLE")


def test_unexpected_error_is_500_without_internals():
    serve("BI_READER", FakeService(RuntimeError('psycopg2 error at "/app/API/x.py": SELECT secret FROM users')))
    body = assert_error(client.get("/api/ltsa/bi/v1/assets"), 500, "BI_INTERNAL_ERROR")
    assert "SELECT" not in body["message"] and "/app/" not in body["message"] and "psycopg2" not in body["message"]


def test_bi_reader_is_confined_to_bi_paths_even_on_auth_only_routes(monkeypatch):
    # Real get_current_user (not overridden): authentication resolves a BI_READER identity,
    # then the central path confinement refuses every non-BI route -- including routes that
    # check no permission at all (e.g. /api/ltsa/mechanical-seal-stock).
    monkeypatch.setattr(dependencies, "_authenticate", lambda authorization: identity("BI_READER"))
    app.dependency_overrides[get_bi_dataset_service] = lambda: FakeService()
    headers = {"Authorization": "Bearer test"}
    assert client.get("/api/ltsa/bi/v1/metadata", headers=headers).status_code == 200
    for path in ["/api/ltsa/mechanical-seal-stock", "/api/ltsa/pumps", "/api/auth/me"]:
        assert client.get(path, headers=headers).status_code == 403, path


def test_other_roles_are_not_path_confined(monkeypatch):
    monkeypatch.setattr(dependencies, "_authenticate", lambda authorization: identity("TAP_ENGINEER"))
    app.dependency_overrides[get_bi_dataset_service] = lambda: FakeService()
    response = client.get("/api/ltsa/bi/v1/metadata", headers={"Authorization": "Bearer test"})
    assert_error(response, 403, "BI_FORBIDDEN")  # refused by bi.read, not by path confinement


def test_bi_machine_basic_auth_success():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = "ltsa_bi_0123456789abcdef01234567"
    secret = "sec_test_secret_12345678901234567890"
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(secret),
        organization_id="org-1",
        description="Power BI Refresh",
        actor="TEST",
    )
    app.dependency_overrides[get_bi_dataset_service] = lambda: FakeService()
    app.dependency_overrides[dependencies.get_bi_machine_credential_repository] = lambda: repo

    b64 = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    res = client.get("/api/ltsa/bi/v1/metadata", headers={"Authorization": f"Basic {b64}"})
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_bi_machine_basic_auth_invalid_secret_returns_401_bi_envelope():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = "ltsa_bi_0123456789abcdef01234567"
    secret = "sec_test_secret_12345678901234567890"
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(secret),
        organization_id="org-1",
        description="Power BI Refresh",
        actor="TEST",
    )
    app.dependency_overrides[get_bi_dataset_service] = lambda: FakeService()
    app.dependency_overrides[dependencies.get_bi_machine_credential_repository] = lambda: repo

    b64 = base64.b64encode(f"{client_id}:wrong_secret".encode()).decode()
    res = client.get("/api/ltsa/bi/v1/metadata", headers={"Authorization": f"Basic {b64}"})
    assert_error(res, 401, "BI_UNAUTHENTICATED")


def test_bi_machine_basic_auth_overlapping_rotation_support():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = "ltsa_bi_0123456789abcdef01234567"
    primary_secret = "sec_primary_secret_12345"
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(primary_secret),
        organization_id="org-1",
        description="Power BI Refresh",
        actor="TEST",
    )
    secondary_secret = "sec_secondary_secret_67890"
    repo.rotate_credential(
        client_id=client_id,
        new_secret_hash=hash_secret(secondary_secret),
        grace_days=7,
        actor="TEST",
    )
    app.dependency_overrides[get_bi_dataset_service] = lambda: FakeService()
    app.dependency_overrides[dependencies.get_bi_machine_credential_repository] = lambda: repo

    # Both primary and secondary authenticate successfully
    b64_primary = base64.b64encode(f"{client_id}:{primary_secret}".encode()).decode()
    res_pri = client.get("/api/ltsa/bi/v1/metadata", headers={"Authorization": f"Basic {b64_primary}"})
    assert res_pri.status_code == 200

    b64_sec = base64.b64encode(f"{client_id}:{secondary_secret}".encode()).decode()
    res_sec = client.get("/api/ltsa/bi/v1/metadata", headers={"Authorization": f"Basic {b64_sec}"})
    assert res_sec.status_code == 200


def test_bi_machine_basic_auth_confined_from_non_bi_routes():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = "ltsa_bi_0123456789abcdef01234567"
    secret = "sec_test_secret_12345678901234567890"
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(secret),
        organization_id="org-1",
        description="Power BI Refresh",
        actor="TEST",
    )
    app.dependency_overrides[dependencies.get_bi_machine_credential_repository] = lambda: repo

    b64 = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    headers = {"Authorization": f"Basic {b64}"}
    # Non-BI routes must reject Basic machine credentials with 403
    for path in ["/api/ltsa/mechanical-seal-stock", "/api/ltsa/pumps", "/api/auth/me"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 403, f"{path} should be 403"

