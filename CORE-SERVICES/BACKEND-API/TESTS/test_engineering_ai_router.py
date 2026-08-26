"""MWO-LTSA-ENGINEERING-AI-ASSET360-NOT-FOUND-020 -- proves POST
/api/ltsa/engineering-ai is registered and behaves per Phase 2's contract:
grounded SUCCESS when evidence exists, honest DATA_GAP (never 404, never
"Error") when it does not, real 404 only for a genuinely unknown/
out-of-scope pump, and a structured error (never an unhandled 500) on a
downstream failure.
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from dependencies import (  # noqa: E402
    get_current_user,
    get_engineering_context_engine,
    get_ltsa_knowledge_service,
    get_pump_gateway,
)
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.ltsa_knowledge_service import LTSAKnowledge  # noqa: E402
from API.recommendation_engine import Evidence, Recommendation  # noqa: E402

client = TestClient(app)

_PUMPS = {"140-P-10B": {"tag_number": "140-P-10B", "area": "HOC", "status": "RUNNING"}}


class FakePumpGateway:
    def get_pump(self, tag_number):
        match = _PUMPS.get(tag_number)
        if match is None:
            return {"success": False, "message": "not found", "data": None}
        return {"success": True, "message": "ok", "data": match}


def _knowledge(recommendation=()):
    return LTSAKnowledge(
        tag_number="140-P-10B", pump=_PUMPS["140-P-10B"], seal=[], inventory=[],
        pm_history=[], cm_history=[], breakdown_history=[], drawings=[],
        recommendation=recommendation, pm_schedules=[], condition_monitoring_schedules=[],
        condition_monitoring_readings=[],
    )


class FakeLTSAKnowledgeService:
    def __init__(self, knowledge):
        self._knowledge = knowledge

    def build(self, tag_number):
        return self._knowledge


class FakeEngineeringContextEngine:
    def __init__(self, summary=None):
        self._summary = summary or {"cm_summary": {"overall_condition": "ABNORMAL"}}

    def build(self, tag_number):
        return self._summary


class RaisingService:
    def build(self, tag_number):
        raise ConnectionError("n8n unreachable")


def _identity(permissions=None):
    return AuthenticatedIdentity(
        user_id="u1", email="u1@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role="TAP_ADMIN",
        permissions=ROLE_PERMISSIONS["TAP_ADMIN"] if permissions is None else permissions,
    )


def _as(identity, *, knowledge_service=None, context_engine=None):
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_pump_gateway] = lambda: FakePumpGateway()
    app.dependency_overrides[get_ltsa_knowledge_service] = lambda: knowledge_service or FakeLTSAKnowledgeService(_knowledge())
    app.dependency_overrides[get_engineering_context_engine] = lambda: context_engine or FakeEngineeringContextEngine()


def _clear():
    for dep in (get_current_user, get_pump_gateway, get_ltsa_knowledge_service, get_engineering_context_engine):
        app.dependency_overrides.pop(dep, None)


def _ask(asset_code="140-P-10B"):
    return client.post(
        "/api/ltsa/engineering-ai",
        json={"asset_code": asset_code, "intent": "summary", "prompt_type": "summary", "trace_id": "trace-1", "workspace": "pump"},
    )


def test_route_is_registered():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ltsa/engineering-ai" in paths
    assert set(paths["/api/ltsa/engineering-ai"]) == {"post"}


def test_valid_pump_with_engineering_data_returns_grounded_success():
    rec = Recommendation(
        id="REC_CRITICAL_CM:140-P-10B", rule_code="REC_CRITICAL_CM", priority=100, category="INSPECTION",
        title="Immediate Inspection", description="Open critical CM report found.",
        evidence=(Evidence(source="CMReport", reference="CM-1", field="severity", value="CRITICAL"),),
        confidence=1.0, action="Dispatch a technician for immediate inspection.",
    )
    _as(_identity(), knowledge_service=FakeLTSAKnowledgeService(_knowledge(recommendation=(rec,))))
    try:
        response = _ask()
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "SUCCESS"
    assert "error" not in body or body.get("error") is None
    assert body["risk"] == "ABNORMAL"
    assert body["confidence"] == 1.0
    assert body["recommendations"] == ["Dispatch a technician for immediate inspection."]
    assert body["findings"] == ["Open critical CM report found."]
    assert "CMReport CM-1" in body["evidence"][0]
    assert body["trace_id"] == "trace-1"


def test_valid_pump_without_recommendation_is_data_gap_not_error():
    _as(_identity(), knowledge_service=FakeLTSAKnowledgeService(_knowledge(recommendation=())))
    try:
        response = _ask()
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "DATA_GAP"
    assert body.get("error") is None
    assert "No engineering recommendation available" in body["summary"]
    assert body["findings"] == []
    assert body["recommendations"] == []


def test_nonexistent_pump_is_true_404():
    _as(_identity())
    try:
        response = _ask(asset_code="DOES-NOT-EXIST")
    finally:
        _clear()

    assert response.status_code == 404


def test_api_failure_returns_structured_error_not_unhandled_500():
    _as(_identity(), knowledge_service=RaisingService())
    try:
        response = _ask()
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "ERROR"
    assert body.get("error")


def test_missing_bearer_token_is_401():
    _clear()
    response = _ask()
    assert response.status_code == 401


def test_insufficient_permission_is_403():
    _as(_identity(permissions=frozenset()))
    try:
        response = _ask()
    finally:
        _clear()
    assert response.status_code == 403
