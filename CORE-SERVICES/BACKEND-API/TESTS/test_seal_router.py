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
    get_import_database_runner,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_lifecycle_event_repository,
    get_seal_master_data_repository,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    get_seal_unit_repository,
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


def _identity(
    role: str, user_id: str = "actor-1", *, data_scope_type: str | None = None, data_scope_value: str | None = None
) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type, data_scope_value=data_scope_value,
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


# --- MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- GET /api/ltsa/seal-units[/{id}] ---


class FakeSealUnitRepository:
    def __init__(self, *, units=None):
        self.units = units if units is not None else []
        self.list_calls = 0
        self.find_calls = []

    def list_all(self):
        self.list_calls += 1
        return self.units

    def find_by_id(self, seal_unit_id):
        self.find_calls.append(seal_unit_id)
        for unit in self.units:
            if unit["seal_unit_id"] == seal_unit_id:
                return unit
        return None


def test_seal_units_routes_are_registered():
    # MWO-LTSA-PHYSICAL-SEAL-001B -- /api/ltsa/seal-units gained POST
    # (registration); the detail route stays GET-only (no update/delete
    # exists for an already-registered unit's identity fields).
    openapi = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seal-units" in openapi
    assert set(openapi["/api/ltsa/seal-units"]) == {"get", "post"}
    assert "/api/ltsa/seal-units/{seal_unit_id}" in openapi
    assert set(openapi["/api/ltsa/seal-units/{seal_unit_id}"]) == {"get"}


def test_list_seal_units_returns_data_and_count():
    fake = FakeSealUnitRepository(units=[{"seal_unit_id": "u1", "seal_code": "JC-TYPE-X"}])
    app.dependency_overrides[get_seal_unit_repository] = lambda: fake

    response = client.get("/api/ltsa/seal-units")

    assert response.status_code == 200
    assert response.json() == {"data": fake.units, "count": 1}
    assert fake.list_calls == 1


def test_list_seal_units_requires_only_seal_read_not_master_edit():
    # Every authenticated LTSA role has seal.read (ROLE_PERMISSIONS
    # confirmed universal); this route must not require master.edit.
    fake = FakeSealUnitRepository(units=[])
    for role in ("PERTAMINA_VIEWER", "JOHN_CRANE_ENGINEER", "TAP_ENGINEER"):
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_seal_unit_repository] = lambda: fake
        response = client.get("/api/ltsa/seal-units")
        assert response.status_code == 200, f"{role} should be able to read seal units"


def test_get_seal_unit_detail_returns_the_matching_unit():
    fake = FakeSealUnitRepository(units=[{"seal_unit_id": "u1", "seal_code": "JC-TYPE-X"}])
    app.dependency_overrides[get_seal_unit_repository] = lambda: fake

    response = client.get("/api/ltsa/seal-units/u1")

    assert response.status_code == 200
    assert response.json() == {"data": {"seal_unit_id": "u1", "seal_code": "JC-TYPE-X"}}
    assert fake.find_calls == ["u1"]


def test_get_seal_unit_detail_404s_for_an_unknown_id():
    fake = FakeSealUnitRepository(units=[])
    app.dependency_overrides[get_seal_unit_repository] = lambda: fake

    response = client.get("/api/ltsa/seal-units/no-such-unit")

    assert response.status_code == 404


def test_no_patch_or_delete_route_exists_for_seal_units_or_lifecycle_events():
    # MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 supersedes the prior
    # identity-foundation MWO's "GET-only" rule with an explicit, narrow
    # exception: exactly one POST (create-event) is now legitimate. What
    # must remain permanently true -- append-only, this MWO's own Hard
    # Rule -- is that PATCH/DELETE never appear anywhere on these paths.
    openapi = client.get("/openapi.json").json()["paths"]
    seal_unit_paths = [p for p in openapi if "seal-unit" in p]
    for path in seal_unit_paths:
        methods = set(openapi[path])
        assert "patch" not in methods and "delete" not in methods, f"{path} must never allow PATCH/DELETE"
        assert methods <= {"get", "post"}, f"{path} must only allow GET/POST"


def test_lifecycle_create_route_is_post_only_no_update_or_delete():
    openapi = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/seal-units/{seal_unit_id}/lifecycle" in openapi
    methods = set(openapi["/api/ltsa/seal-units/{seal_unit_id}/lifecycle"])
    assert methods == {"get", "post"}
    assert "/api/ltsa/seal-lifecycle-events/{event_id}" in openapi
    assert set(openapi["/api/ltsa/seal-lifecycle-events/{event_id}"]) == {"get"}


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


# --- MWO-LTSA-SEAL-LIFECYCLE-EVENT-LEDGER-001 -- lifecycle event ledger routes ---
#
# GET routes are exercised against a fake SealLifecycleEventRepository
# (matching FakeSealUnitRepository's own precedent above). POST is
# exercised against a fake `runner` -- apply_lifecycle_event() is
# imported directly into the router (not itself a FastAPI dependency),
# so only its `runner` parameter is injectable; this reuses
# test_record_edit_router.py's own FakeRunner pattern exactly: the fake
# returns a canned JSON row from query_scalar(), and the REAL service
# function's SQL-construction/response-parsing logic runs for real
# against it -- no live database needed for router-level proofs.


class FakeSealLifecycleEventRepository:
    def __init__(self, *, events=None):
        self.events = events if events is not None else []

    def find_by_id(self, event_id):
        for event in self.events:
            if event["event_id"] == event_id:
                return event
        return None

    def list_by_seal_unit(self, seal_unit_id):
        return [e for e in self.events if e["seal_unit_id"] == seal_unit_id]

    def list_by_pump(self, pump_tag_number):
        return [e for e in self.events if e.get("pump_tag_number") == pump_tag_number]


class FakePumpGateway:
    def __init__(self, area_by_tag):
        self.area_by_tag = area_by_tag

    def get_pump(self, tag_number):
        if tag_number not in self.area_by_tag:
            return {"success": False}
        return {"success": True, "data": {"tag_number": tag_number, "area": self.area_by_tag[tag_number]}}


class FakeRunner:
    """Mirrors test_record_edit_router.py's own FakeRunner: `outcome` is
    the already-JSON-encoded row apply_lifecycle_event()'s single
    compound SQL statement would have returned from query_scalar()."""

    def __init__(self, outcome: str):
        self.outcome = outcome
        self.query_scalar_calls: list[str] = []

    def query_scalar(self, sql):
        self.query_scalar_calls.append(sql)
        return self.outcome


# apply_lifecycle_event() rejects a non-UUID seal_unit_id before ever
# touching the runner (the malformed-UUID closure this MWO also
# requires) -- POST-route tests must use a syntactically valid UUID in
# the path so the fake runner's canned outcome is actually reached.
_VALID_SEAL_UNIT_ID = "11111111-1111-4111-8111-111111111111"


def _lifecycle_outcome(
    *, unit_found=1, status_matched=1, compat_matched=1, event_id="evt-1", seal_unit_id="unit-1",
    event_type="INSTALL", pump_tag_number="110-P-9A", created_by="server-actor",
):
    import json as _json

    event_row = {
        "event_id": event_id, "seal_unit_id": seal_unit_id, "event_type": event_type,
        "pump_tag_number": pump_tag_number, "event_at": "2026-08-20T00:00:00+00:00",
        "reason": None, "notes": None, "source_reference": None,
        "created_by": created_by, "created_at": "2026-08-20T00:00:00+00:00",
    }
    event_json = _json.dumps([event_row]) if status_matched and compat_matched and unit_found else "[]"
    return _json.dumps(
        {
            "unit_found": unit_found, "status_matched": status_matched,
            "compat_matched": compat_matched, "event_json": event_json,
        }
    )


def test_list_seal_unit_lifecycle_returns_404_when_the_unit_does_not_exist():
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=[])
    app.dependency_overrides[get_seal_lifecycle_event_repository] = lambda: FakeSealLifecycleEventRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})

    response = client.get("/api/ltsa/seal-units/no-such-unit/lifecycle")

    assert response.status_code == 404


def test_list_seal_unit_lifecycle_returns_data_and_count_for_an_unrestricted_role():
    unit = {"seal_unit_id": _VALID_SEAL_UNIT_ID, "seal_code": "JC-TYPE-X"}
    events = [
        {"event_id": "evt-1", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "REGISTERED", "pump_tag_number": None},
        {"event_id": "evt-2", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL", "pump_tag_number": "110-P-9A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = lambda: FakeSealUnitRepository(units=[unit])
    app.dependency_overrides[get_seal_lifecycle_event_repository] = (
        lambda: FakeSealLifecycleEventRepository(events=events)
    )
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({"110-P-9A": "HOC"})
    # SUPERUSER/TAP_ADMIN/TAP_ENGINEER/JOHN_CRANE_ENGINEER are the real,
    # current _UNRESTRICTED_ROLES set (auth_service.py) -- unlike the two
    # Pertamina roles (covered separately below), these see every event
    # regardless of pump area, with no scope configured at all.
    for role in ("SUPERUSER", "TAP_ADMIN", "TAP_ENGINEER", "JOHN_CRANE_ENGINEER"):
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle")
        assert response.status_code == 200, f"{role} should be able to read lifecycle events"
        assert response.json()["count"] == 2, f"{role} should see every event"


def test_get_seal_lifecycle_event_returns_404_for_an_unknown_event():
    app.dependency_overrides[get_seal_lifecycle_event_repository] = lambda: FakeSealLifecycleEventRepository()
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway({})

    response = client.get("/api/ltsa/seal-lifecycle-events/no-such-event")

    assert response.status_code == 404


def test_area_scoped_identity_sees_only_in_scope_pump_events_and_all_pumpless_events():
    # Pump-associated events must obey pump area scope; a pumpless event
    # (e.g. REGISTERED) must never be hidden -- it carries no pump-area
    # information to leak (this MWO's own AREA AUTHORIZATION rule).
    events = [
        {"event_id": "evt-registered", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "REGISTERED", "pump_tag_number": None},
        {"event_id": "evt-in-scope", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL", "pump_tag_number": "110-P-9A"},
        {"event_id": "evt-out-of-scope", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL", "pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID, "seal_code": "JC-TYPE-X"}])
    )
    app.dependency_overrides[get_seal_lifecycle_event_repository] = (
        lambda: FakeSealLifecycleEventRepository(events=events)
    )
    app.dependency_overrides[get_pump_gateway] = (
        lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    )
    app.dependency_overrides[get_current_user] = (
        lambda: _identity("PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HOC")
    )

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle")

    assert response.status_code == 200
    ids = {e["event_id"] for e in response.json()["data"]}
    assert ids == {"evt-registered", "evt-in-scope"}

    # The single-event GET route must apply the identical rule -- an
    # out-of-scope event is reported as 404, never disclosed to exist.
    in_scope_response = client.get("/api/ltsa/seal-lifecycle-events/evt-in-scope")
    assert in_scope_response.status_code == 200
    out_of_scope_response = client.get("/api/ltsa/seal-lifecycle-events/evt-out-of-scope")
    assert out_of_scope_response.status_code == 404


def test_unrestricted_role_sees_every_event_regardless_of_pump_area():
    events = [
        {"event_id": "evt-a", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL", "pump_tag_number": "110-P-9A"},
        {"event_id": "evt-b", "seal_unit_id": _VALID_SEAL_UNIT_ID, "event_type": "INSTALL", "pump_tag_number": "211-P-1A"},
    ]
    app.dependency_overrides[get_seal_unit_repository] = (
        lambda: FakeSealUnitRepository(units=[{"seal_unit_id": _VALID_SEAL_UNIT_ID, "seal_code": "JC-TYPE-X"}])
    )
    app.dependency_overrides[get_seal_lifecycle_event_repository] = (
        lambda: FakeSealLifecycleEventRepository(events=events)
    )
    app.dependency_overrides[get_pump_gateway] = (
        lambda: FakePumpGateway({"110-P-9A": "HOC", "211-P-1A": "HCC"})
    )
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY

    response = client.get(f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle")

    assert response.status_code == 200
    assert {e["event_id"] for e in response.json()["data"]} == {"evt-a", "evt-b"}


def test_create_lifecycle_event_succeeds_for_superuser_and_tap_admin():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = FakeRunner(_lifecycle_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner

        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
            json={"event_type": "INSTALL", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A"},
        )

        assert response.status_code == 200, f"{role} should be authorized to write lifecycle events"
        assert response.json()["data"]["event_type"] == "INSTALL"


def test_create_lifecycle_event_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = FakeRunner(_lifecycle_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner

        response = client.post(
            f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
            json={"event_type": "INSTALL", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A"},
        )

        assert response.status_code == 403, f"{role} must be denied seal.lifecycle_write"
        assert fake_runner.query_scalar_calls == []


def test_create_lifecycle_event_actor_is_always_the_authenticated_user_never_the_request_body():
    # SealLifecycleEventCreateRequest has no created_by field at all, so a
    # client attempting to smuggle one is silently dropped by pydantic --
    # the value actually reaching apply_lifecycle_event's SQL must be the
    # real authenticated actor, provable here by inspecting the literal
    # SQL text the fake runner captured (created_by is inlined via _sql()).
    fake_runner = FakeRunner(_lifecycle_outcome(created_by="real-actor"))
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN", user_id="real-actor")
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
        json={
            "event_type": "INSTALL", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A",
            "created_by": "spoofed-actor",
        },
    )

    assert response.status_code == 200
    sql = fake_runner.query_scalar_calls[0]
    assert "real-actor" in sql
    assert "spoofed-actor" not in sql


def test_create_lifecycle_event_returns_404_when_the_seal_unit_is_not_found():
    # A syntactically valid but non-existent UUID -- proves the 404 comes
    # from apply_lifecycle_event's own unit_found=0 outcome, distinct from
    # the malformed-UUID short-circuit proven separately in the
    # disposable-Postgres suite.
    fake_runner = FakeRunner(_lifecycle_outcome(unit_found=0, status_matched=0, compat_matched=0))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        "/api/ltsa/seal-units/22222222-2222-4222-8222-222222222222/lifecycle",
        json={"event_type": "INSTALL", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A"},
    )

    assert response.status_code == 404
    assert fake_runner.query_scalar_calls, "the runner must actually be reached for this case"


def test_create_lifecycle_event_returns_409_for_an_invalid_transition():
    fake_runner = FakeRunner(_lifecycle_outcome(status_matched=0, compat_matched=0))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
        json={"event_type": "REMOVE", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A", "reason": "test"},
    )

    assert response.status_code == 409


def test_create_lifecycle_event_returns_422_for_an_incompatible_pump():
    fake_runner = FakeRunner(_lifecycle_outcome(compat_matched=0))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
        json={"event_type": "INSTALL", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A"},
    )

    assert response.status_code == 422


def test_create_lifecycle_event_returns_422_when_a_required_reason_is_missing():
    fake_runner = FakeRunner(_lifecycle_outcome())
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner

    response = client.post(
        f"/api/ltsa/seal-units/{_VALID_SEAL_UNIT_ID}/lifecycle",
        json={"event_type": "REMOVE", "event_at": "2026-08-20T00:00:00Z", "pump_tag_number": "110-P-9A"},
    )

    assert response.status_code == 422
    assert fake_runner.query_scalar_calls == []


# --- MWO-LTSA-PHYSICAL-SEAL-001B -- POST /api/ltsa/seal-units (registration) ---


def _register_outcome(*, seal_matched=1, serial_matched=1, seal_code="JC-TYPE-X", serial_number=None):
    import json as _json

    unit_row = {
        "seal_unit_id": "11111111-1111-4111-8111-111111111111", "seal_code": seal_code,
        "serial_number": serial_number, "status": "IN_STOCK", "current_pump_tag_number": None,
        "created_at": "2026-08-20T00:00:00", "updated_at": "2026-08-20T00:00:00",
    }
    ok = seal_matched and serial_matched
    return _json.dumps(
        {
            "seal_matched": seal_matched, "serial_matched": serial_matched,
            "unit_json": _json.dumps([unit_row]) if ok else "[]",
        }
    )


def test_register_seal_unit_route_exists_post_only_alongside_existing_get():
    openapi = client.get("/openapi.json").json()["paths"]
    assert set(openapi["/api/ltsa/seal-units"]) == {"get", "post"}


def test_register_seal_unit_succeeds_for_superuser_and_tap_admin_only():
    for role in ("SUPERUSER", "TAP_ADMIN"):
        fake_runner = FakeRunner(_register_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X"})
        assert response.status_code == 200, f"{role} should be authorized"
        assert response.json()["data"]["status"] == "IN_STOCK"
        assert response.json()["data"]["current_pump_tag_number"] is None


def test_register_seal_unit_denied_for_read_only_roles():
    for role in ("TAP_ENGINEER", "JOHN_CRANE_ENGINEER", "PERTAMINA_ENGINEER", "PERTAMINA_VIEWER"):
        fake_runner = FakeRunner(_register_outcome())
        app.dependency_overrides[get_current_user] = lambda role=role: _identity(role)
        app.dependency_overrides[get_import_database_runner] = lambda fake_runner=fake_runner: fake_runner
        response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X"})
        assert response.status_code == 403, f"{role} must be denied"
        assert fake_runner.query_scalar_calls == []


def test_register_seal_unit_rejects_unauthenticated_requests():
    app.dependency_overrides.clear()  # no get_current_user override -- no bearer token at all
    response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X"})
    assert response.status_code == 401


def test_register_seal_unit_maps_unknown_seal_code_to_404():
    fake_runner = FakeRunner(_register_outcome(seal_matched=0, serial_matched=0))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post("/api/ltsa/seal-units", json={"seal_code": "NOT-A-REAL-CODE"})
    assert response.status_code == 404


def test_register_seal_unit_maps_duplicate_serial_number_to_409():
    fake_runner = FakeRunner(_register_outcome(serial_matched=0))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X", "serial_number": "SN-DUP"})
    assert response.status_code == 409


def test_register_seal_unit_persists_a_supplied_serial_number():
    fake_runner = FakeRunner(_register_outcome(serial_number="SN-0001"))
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X", "serial_number": "SN-0001"})
    assert response.status_code == 200
    assert response.json()["data"]["serial_number"] == "SN-0001"


def test_register_seal_unit_allows_a_null_serial_number():
    fake_runner = FakeRunner(_register_outcome())
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post("/api/ltsa/seal-units", json={"seal_code": "JC-TYPE-X"})
    assert response.status_code == 200
    assert response.json()["data"]["serial_number"] is None


def test_register_seal_unit_request_body_has_no_pump_or_lifecycle_fields():
    # Registration and installation are separate domain actions (this
    # MWO's own explicit rule) -- a client attempting to smuggle
    # current_pump_tag_number/status into the request body has no field
    # to land in: SealUnitRegisterRequest only has seal_code/serial_number,
    # so pydantic silently drops anything else, never reaching the service.
    fake_runner = FakeRunner(_register_outcome())
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    app.dependency_overrides[get_import_database_runner] = lambda: fake_runner
    response = client.post(
        "/api/ltsa/seal-units",
        json={"seal_code": "JC-TYPE-X", "current_pump_tag_number": "110-P-9A", "status": "INSTALLED"},
    )
    assert response.status_code == 200
    sql = fake_runner.query_scalar_calls[0]
    assert "INSTALLED" not in sql
    assert "110-P-9A" not in sql
