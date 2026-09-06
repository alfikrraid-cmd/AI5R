"""AI5R-PHASE4E3 -- POST /api/ltsa/pm-schedules/bulk: maintenance.write
authorization (Section K -- reused, never widened; actor always comes
from the authenticated identity, never the request body), and that a
row-level validation failure surfaces as a row-correlated, human-readable
422 (Section G: "Never: [object Object]"), never a partial create."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user, get_pm_schedule_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.operational_registry_repository import BulkPMScheduleValidationError  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakePMScheduleRepository:
    def __init__(self, *, bulk_result=None, bulk_error: BulkPMScheduleValidationError | None = None):
        self._bulk_result = bulk_result if bulk_result is not None else []
        self._bulk_error = bulk_error
        self.bulk_calls: list[dict] = []

    def bulk_create(self, *, rows, actor):
        self.bulk_calls.append({"rows": rows, "actor": actor})
        if self._bulk_error is not None:
            raise self._bulk_error
        return self._bulk_result


def _override(role: str, user_id: str = "actor-1", repository=None):
    fake = repository or FakePMScheduleRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[get_pm_schedule_repository] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _row(client_row_id="row-1", asset_code="211-P-1A", **overrides):
    row = {
        "client_row_id": client_row_id,
        "asset_code": asset_code,
        "frequency": "MONTHLY",
        "trigger_type": "CALENDAR",
        "effective_date": "2026-10-01",
    }
    row.update(overrides)
    return row


def test_tap_engineer_with_maintenance_write_can_bulk_create():
    fake = _override(
        "TAP_ENGINEER",
        repository=FakePMScheduleRepository(bulk_result=[{"client_row_id": "row-1", "pm_schedule_code": "PMSCH-AAAAAAAAAAAA"}]),
    )
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row()]})

    assert response.status_code == 200
    assert response.json()["data"] == [{"client_row_id": "row-1", "pm_schedule_code": "PMSCH-AAAAAAAAAAAA"}]
    assert fake.bulk_calls[0]["actor"] == "actor-1"


def test_pertamina_viewer_cannot_bulk_create():
    _override("PERTAMINA_VIEWER")
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row()]})
    assert response.status_code == 403


def test_pertamina_engineer_cannot_bulk_create():
    _override("PERTAMINA_ENGINEER")
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row()]})
    assert response.status_code == 403


def test_anonymous_bulk_create_is_401():
    app.dependency_overrides.clear()
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row()]})
    assert response.status_code == 401


def test_actor_always_comes_from_authenticated_identity_never_request_body():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row()]})
    assert fake.bulk_calls[0]["actor"] == "real-actor"


def test_row_validation_error_surfaces_as_a_row_correlated_readable_422_never_object_object():
    fake = _override(
        "TAP_ENGINEER",
        repository=FakePMScheduleRepository(
            bulk_error=BulkPMScheduleValidationError({"row-2": "Unknown pump: NOT-REAL"})
        ),
    )
    response = client.post(
        "/api/ltsa/pm-schedules/bulk",
        json={"rows": [_row("row-1"), _row("row-2", asset_code="NOT-REAL")]},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["client_row_id"] == "row-2"
    assert "Unknown pump" in detail[0]["msg"]
    assert "object Object" not in str(detail)
    assert len(fake.bulk_calls) == 1  # repository was called once, atomically, no retry/partial loop


def test_empty_rows_is_rejected_before_reaching_the_repository():
    fake = _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": []})

    assert response.status_code == 422
    assert fake.bulk_calls == []


def test_invalid_frequency_is_rejected_before_reaching_the_repository():
    fake = _override("TAP_ENGINEER")
    response = client.post("/api/ltsa/pm-schedules/bulk", json={"rows": [_row(frequency="YEARLY")]})

    assert response.status_code == 422
    assert fake.bulk_calls == []
