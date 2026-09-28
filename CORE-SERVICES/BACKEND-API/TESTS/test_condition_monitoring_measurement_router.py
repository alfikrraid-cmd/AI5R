"""MWO-LTSA-REPORTING-R4 -- condition_monitoring_measurement router
tests: RBAC (read/write/area-MA), request/response shape, and
repository-exception -> HTTP-status mapping. Fake repository, standalone
app (this router is not wired into main.py yet -- see
routers/condition_monitoring_measurement.py's own header), same pattern
as test_ltsa_finding_router.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from routers import condition_monitoring_measurement as router_module  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.condition_monitoring_measurement_repository import EmptyMeasurementValue  # noqa: E402

app = FastAPI()
app.include_router(router_module.router)
client = TestClient(app)


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, user_id="actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
    )


class FakeMeasurementRepository:
    def __init__(self):
        self.calls: list[tuple] = []
        self._raise_on_create: Exception | None = None
        self._raise_on_update: Exception | None = None
        self._measurements = {"MEAS-1": {"measurement_id": "MEAS-1", "reading_id": "CMONR-1", "value_numeric": 1, "value_text": None}}

    def list_by_reading(self, reading_id, **kwargs):
        self.calls.append(("list_by_reading", reading_id, kwargs))
        if reading_id == "CMONR-MISSING":
            return None
        scope = kwargs.get("scope")
        if scope is not None and "HOC" not in scope:
            return []
        return [row for row in self._measurements.values() if row["reading_id"] == reading_id]

    def find_by_id(self, measurement_id):
        self.calls.append(("find_by_id", measurement_id))
        return self._measurements.get(measurement_id)

    def create(self, **kwargs):
        self.calls.append(("create", kwargs))
        if self._raise_on_create:
            raise self._raise_on_create
        if kwargs["reading_id"] == "CMONR-MISSING":
            return None
        row = {"measurement_id": "MEAS-NEW", **kwargs}
        self._measurements["MEAS-NEW"] = row
        return row

    def update(self, measurement_id, **kwargs):
        self.calls.append(("update", measurement_id, kwargs))
        if self._raise_on_update:
            raise self._raise_on_update
        if measurement_id not in self._measurements:
            return None
        self._measurements[measurement_id] = {**self._measurements[measurement_id], **kwargs.get("values", {})}
        return self._measurements[measurement_id]


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, *, repository=None, **identity_kwargs):
    fake = repository or FakeMeasurementRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, **identity_kwargs)
    app.dependency_overrides[router_module.get_condition_monitoring_measurement_repository] = lambda: fake
    return fake


# ---- RBAC read ----

def test_role_without_condition_read_denied_list():
    _override("PERTAMINA_VIEWER")
    response = client.get("/api/ltsa/condition-monitoring/readings/CMONR-1/measurements")
    assert response.status_code == 403


def test_role_with_condition_read_allowed_list():
    _override("PERTAMINA_ENGINEER")
    response = client.get("/api/ltsa/condition-monitoring/readings/CMONR-1/measurements")
    assert response.status_code == 200


def test_list_reading_not_found():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/condition-monitoring/readings/CMONR-MISSING/measurements")
    assert response.status_code == 404


# ---- RBAC write ----

def test_role_without_maintenance_write_denied_create():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring/readings/CMONR-1/measurements",
        json={"measurement_label": "x", "value_numeric": 1},
    )
    assert response.status_code == 403


def test_role_with_maintenance_write_allowed_create():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring/readings/CMONR-1/measurements",
        json={"measurement_label": "x", "value_numeric": 1},
    )
    assert response.status_code == 200
    assert response.json()["data"]["measurement_id"] == "MEAS-NEW"


def test_create_parent_not_found():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring/readings/CMONR-MISSING/measurements",
        json={"measurement_label": "x", "value_numeric": 1},
    )
    assert response.status_code == 404


def test_create_empty_value_returns_400():
    fake = FakeMeasurementRepository()
    fake._raise_on_create = EmptyMeasurementValue("need a value")
    _override("TAP_ENGINEER", repository=fake)
    response = client.post(
        "/api/ltsa/condition-monitoring/readings/CMONR-1/measurements",
        json={"measurement_label": "x"},
    )
    assert response.status_code == 400


# ---- update ----

def test_update_not_found_returns_404():
    _override("TAP_ENGINEER")
    response = client.patch("/api/ltsa/condition-monitoring/measurements/MEAS-MISSING", json={"value_numeric": 2})
    assert response.status_code == 404


def test_update_ok():
    _override("TAP_ENGINEER")
    response = client.patch("/api/ltsa/condition-monitoring/measurements/MEAS-1", json={"value_numeric": 2})
    assert response.status_code == 200
    assert response.json()["data"]["value_numeric"] == 2


def test_update_empty_value_returns_400():
    fake = FakeMeasurementRepository()
    fake._raise_on_update = EmptyMeasurementValue("need a value")
    _override("TAP_ENGINEER", repository=fake)
    response = client.patch("/api/ltsa/condition-monitoring/measurements/MEAS-1", json={"value_numeric": None})
    assert response.status_code == 400


# ---- area/MA restriction ----

def test_get_measurement_outside_scope_not_found():
    fake = FakeMeasurementRepository()
    _override("PERTAMINA_ENGINEER", data_scope_type="MA", data_scope_value="MA3", repository=fake)
    response = client.get("/api/ltsa/condition-monitoring/measurements/MEAS-1")
    assert response.status_code == 404
