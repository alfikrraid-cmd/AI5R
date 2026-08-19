import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import get_current_user, get_fleet_executive_summary_service, get_fleet_reliability_service
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity
from API.fleet_executive_summary import FleetExecutiveSummary, TopRisk
from API.fleet_reliability_service import FleetReliability

client = TestClient(app)

# MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
_SUPERUSER_IDENTITY = AuthenticatedIdentity(
    user_id="test-superuser", email="test-superuser@tap.internal",
    organization_id="test-org-tap", organization_code="TAP",
    role="TAP_ADMIN", permissions=ROLE_PERMISSIONS["TAP_ADMIN"],
)




class FakeFleetReliabilityService:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.scopes_seen = []

    def build(self, *, scope=None):
        self.calls += 1
        self.scopes_seen.append(scope)
        return self.result


def _result(**overrides):
    defaults = dict(
        pump_count=2,
        fleet_health_score=55.0,
        fleet_mtbf_days=15.0,
        fleet_mttr_hours=5.0,
        fleet_availability=98.63,
        total_breakdown_count=1,
        total_critical_spare_count=1,
    )
    defaults.update(overrides)
    return FleetReliability(**defaults)


def _override(result=None):
    fake = FakeFleetReliabilityService(result if result is not None else _result())
    app.dependency_overrides[get_fleet_reliability_service] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    # MWO-LTSA-AUTH-001 -- see test_pumps_knowledge_router.py's identical fixture.
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: _SUPERUSER_IDENTITY
    yield
    app.dependency_overrides.clear()


def test_fleet_reliability_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/ltsa/fleet/reliability" in paths


def test_fleet_reliability_route_allows_only_get():
    methods = client.get("/openapi.json").json()["paths"]["/api/ltsa/fleet/reliability"]

    assert set(methods) == {"get"}


def test_get_fleet_reliability_returns_200():
    _override()

    response = client.get("/api/ltsa/fleet/reliability")

    assert response.status_code == 200


def test_get_fleet_reliability_calls_the_service_exactly_once():
    fake = _override()

    client.get("/api/ltsa/fleet/reliability")

    assert fake.calls == 1


def test_get_fleet_reliability_response_shape_matches_the_service_result_unchanged():
    _override(result=_result(pump_count=3, fleet_health_score=80))

    response = client.get("/api/ltsa/fleet/reliability").json()

    assert response["success"] is True
    assert response["data"] == {
        "pump_count": 3,
        "fleet_health_score": 80,
        "fleet_mtbf_days": 15.0,
        "fleet_mttr_hours": 5.0,
        "fleet_availability": 98.63,
        "total_breakdown_count": 1,
        "total_critical_spare_count": 1,
    }


def test_get_fleet_reliability_none_fields_serialize_as_json_null():
    _override(result=_result(fleet_mtbf_days=None, fleet_mttr_hours=None, fleet_availability=None))

    data = client.get("/api/ltsa/fleet/reliability").json()["data"]

    assert data["fleet_mtbf_days"] is None
    assert data["fleet_mttr_hours"] is None
    assert data["fleet_availability"] is None


# MWO-LTSA-038A -- Power BI API: one endpoint exposing FleetExecutiveSummary
# (MWO-LTSA-037E) + FleetInsight (MWO-LTSA-037F, derived from the same
# summary, never a second fetch/service). Router only: no filtering, no
# derivation -- .build()'s own result and build_fleet_insight()'s own pure
# field selection are used unchanged, the same "reused shape, not
# redefined" discipline every other endpoint in this file already follows.


class FakeFleetExecutiveSummaryService:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.scopes_seen = []

    def build(self, *, scope=None):
        self.calls += 1
        self.scopes_seen.append(scope)
        return self.result


def _top_risk(**overrides):
    defaults = dict(
        tag_number="641-P-5",
        rule_code="REC_CRITICAL_CM",
        title="Immediate Inspection",
        priority=100,
        action="Dispatch a technician for immediate inspection.",
        description="An open Corrective Maintenance report with critical or major severity was found.",
    )
    defaults.update(overrides)
    return TopRisk(**defaults)


def _summary(**overrides):
    defaults = dict(
        overall_health=55.0,
        fleet_status="ATTENTION",
        critical_asset_count=1,
        fleet_availability=98.63,
        fleet_mtbf_days=42.3,
        fleet_mttr_hours=6.25,
        breakdown_count=2,
        critical_spare_count=1,
        top_risks=(_top_risk(),),
    )
    defaults.update(overrides)
    return FleetExecutiveSummary(**defaults)


def _override_summary(result=None):
    fake = FakeFleetExecutiveSummaryService(result if result is not None else _summary())
    app.dependency_overrides[get_fleet_executive_summary_service] = lambda: fake
    return fake


def test_powerbi_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/ltsa/fleet/powerbi" in paths


def test_powerbi_route_allows_only_get():
    methods = client.get("/openapi.json").json()["paths"]["/api/ltsa/fleet/powerbi"]

    assert set(methods) == {"get"}


def test_get_powerbi_returns_200():
    _override_summary()

    response = client.get("/api/ltsa/fleet/powerbi")

    assert response.status_code == 200


def test_get_powerbi_calls_fleet_executive_summary_service_exactly_once_one_fetch():
    fake = _override_summary()

    client.get("/api/ltsa/fleet/powerbi")

    assert fake.calls == 1


def test_get_powerbi_response_includes_fleet_executive_summary_fields_unchanged():
    _override_summary(result=_summary(overall_health=72.0, fleet_status="NORMAL", critical_asset_count=0))

    data = client.get("/api/ltsa/fleet/powerbi").json()["data"]

    assert data["overall_health"] == 72.0
    assert data["fleet_status"] == "NORMAL"
    assert data["critical_asset_count"] == 0
    assert data["fleet_availability"] == 98.63
    assert data["fleet_mtbf_days"] == 42.3
    assert data["fleet_mttr_hours"] == 6.25
    assert data["breakdown_count"] == 2
    assert data["critical_spare_count"] == 1


def test_get_powerbi_mtbf_and_mttr_serialize_as_json_null_when_unavailable():
    # MWO-LTSA-038B -- added to FleetExecutiveSummary as a pure pass-through
    # from FleetReliability; must stay None-safe, never fabricated.
    _override_summary(result=_summary(fleet_mtbf_days=None, fleet_mttr_hours=None))

    data = client.get("/api/ltsa/fleet/powerbi").json()["data"]

    assert data["fleet_mtbf_days"] is None
    assert data["fleet_mttr_hours"] is None


def test_get_powerbi_response_includes_top_risks_unchanged():
    _override_summary(result=_summary(top_risks=(_top_risk(tag_number="P-9", priority=90),)))

    data = client.get("/api/ltsa/fleet/powerbi").json()["data"]

    assert data["top_risks"] == [
        {
            "tag_number": "P-9",
            "rule_code": "REC_CRITICAL_CM",
            "title": "Immediate Inspection",
            "priority": 90,
            "action": "Dispatch a technician for immediate inspection.",
            "description": "An open Corrective Maintenance report with critical or major severity was found.",
        }
    ]


def test_get_powerbi_response_includes_insight_derived_from_the_same_summary_no_duplicate_calculation():
    _override_summary(
        result=_summary(top_risks=(_top_risk(priority=100, action="Dispatch now.", description="Critical CM open."),))
    )

    data = client.get("/api/ltsa/fleet/powerbi").json()["data"]

    assert data["insight"]["priority"] == 100
    assert data["insight"]["action"] == "Dispatch now."
    assert data["insight"]["reason"] == "Critical CM open."
    assert "summary" in data["insight"]


def test_get_powerbi_insight_is_none_when_no_top_risks():
    _override_summary(result=_summary(top_risks=()))

    data = client.get("/api/ltsa/fleet/powerbi").json()["data"]

    assert data["insight"] is None


# MWO-LTSA-038C -- Power BI dataset contract: dataset_version + generated_at
# added as top-level response envelope metadata (alongside success/data,
# the same envelope-vs-payload split get_ltsa_pump_knowledge already uses
# for tag_number), not inside `data` -- these describe the response
# itself, not fleet data, so they don't belong on FleetExecutiveSummary/
# FleetInsight. Same GET /api/ltsa/fleet/powerbi endpoint, no new route,
# no scheduler, no refresh job, no cache -- generated_at is computed fresh
# on every request, dataset_version is a static constant.


def test_get_powerbi_response_includes_dataset_version():
    _override_summary()

    response = client.get("/api/ltsa/fleet/powerbi").json()

    assert response["dataset_version"] == "1.0.0"


def test_get_powerbi_response_includes_generated_at_as_an_iso_timestamp():
    _override_summary()

    response = client.get("/api/ltsa/fleet/powerbi").json()

    generated_at = response["generated_at"]
    assert isinstance(generated_at, str)
    # Round-trips through datetime.fromisoformat -- proves it is a real
    # ISO 8601 timestamp, not a placeholder string.
    from datetime import datetime

    datetime.fromisoformat(generated_at)


def test_get_powerbi_generated_at_is_fresh_on_every_request_no_cache():
    import time

    _override_summary()

    first = client.get("/api/ltsa/fleet/powerbi").json()["generated_at"]
    time.sleep(0.01)
    second = client.get("/api/ltsa/fleet/powerbi").json()["generated_at"]

    assert first != second


def test_get_powerbi_dataset_version_and_generated_at_are_top_level_not_inside_data():
    _override_summary()

    response = client.get("/api/ltsa/fleet/powerbi").json()

    assert "dataset_version" not in response["data"]
    assert "generated_at" not in response["data"]


def test_get_powerbi_does_not_call_fleet_executive_summary_service_more_than_once_no_duplicate_api():
    fake = _override_summary()

    client.get("/api/ltsa/fleet/powerbi")

    assert fake.calls == 1
