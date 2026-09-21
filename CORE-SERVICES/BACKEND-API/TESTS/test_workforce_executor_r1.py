import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT / "AI5R-SDK", ROOT / "CORE-SERVICES", ROOT / "CORE-SERVICES/BACKEND-API"):
    sys.path.insert(0, str(path))

import dependencies as deps
from routers.workforce import router
from API.auth_service import AuthenticatedIdentity
from API.engineering_ai_client import EngineeringAIClient
from API.workforce_run_repository import RunConflict, WorkforceRunRepository
from API.workforce_service import WorkforceService
from API.workforce_text_executor import MISSION_TYPE, SYNTHETIC_TEXT, WorkforceTextExecutor
from AI_RUNTIME.ROUTER.router import Router
from AI_RUNTIME.ROUTER.provider_selector import ProviderSelector
from AI_RUNTIME.ROUTER.routing_policy import parse_routing_policy, RoutingMode
from OSA.LLM_PROVIDER import LLMResponse, MockLLMProvider


class FakeProvider(MockLLMProvider):
    def __init__(self, name="DAHONO", fail=False):
        self.provider_name, self.fail, self.calls = name, fail, 0

    def generate(self, request):
        self.calls += 1
        assert request.prompt == SYNTHETIC_TEXT
        assert request.metadata == {"mission_type": MISSION_TYPE}
        if self.fail:
            raise RuntimeError("sensitive exception must never be persisted")
        return LLMResponse(self.provider_name, "actual-model", "Synthetic draft", "stop")


def client_for(*providers):
    router = Router(provider_selector=ProviderSelector(routing_policy=parse_routing_policy("DAHONO_PRIMARY")))
    for provider in providers:
        router.register_provider(provider)
    return EngineeringAIClient(router)


def actor(*permissions, user="server-user", org="org"):
    return AuthenticatedIdentity(user, None, org, "TAP", "TAP_ENGINEER", frozenset(permissions))


@pytest.fixture
def setup(tmp_path):
    repo = WorkforceRunRepository(tmp_path / "pilot.sqlite3")
    service = WorkforceService()
    provider = FakeProvider()
    ai = client_for(provider)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[deps.get_workforce_run_repository] = lambda: repo
    app.dependency_overrides[deps.get_workforce_service] = lambda: service
    app.dependency_overrides[deps.get_workforce_pilot_ai_client] = lambda: ai
    return app, repo, service, provider, ai


def start(service, repo, ai, key="key"):
    return service.start_pilot(actor=actor(), repository=repo, executor=WorkforceTextExecutor(ai),
                               mission_type=MISSION_TYPE, input_text=SYNTHETIC_TEXT, idempotency_key=key)


@pytest.mark.parametrize("fallback", [False, True])
def test_provenance_and_reopen(setup, fallback):
    _, repo, service, provider, ai = setup
    if fallback:
        provider.fail = True
        ai = client_for(provider, FakeProvider("OPENAI"))
    run = start(service, repo, ai)
    assert run["status"] == "AWAITING_REVIEW"
    assert run["requested_policy"] == "DAHONO_PRIMARY"
    assert run["actual_provider"] == ("OPENAI" if fallback else "DAHONO")
    assert run["actual_model"] == "actual-model"
    assert run["finish_reason"] == "stop"
    assert run["fallback_used"] is fallback
    assert run["outcome"] == ("FALLBACK_SUCCESS" if fallback else "DAHONO_SUCCESS")
    assert run["employee"]["position_id"] == "DOCUMENTATION_ENGINEER"
    assert run["elapsed_ms"] >= 0 and run["started_at"] and run["completed_at"]
    reopened = WorkforceRunRepository(repo.path)
    assert reopened.get(run["run_id"]) == run
    assert start(service, reopened, ai) == run
    assert provider.calls == 1


@pytest.mark.parametrize("decision,status", [("APPROVE", "COMPLETED"), ("REJECT", "REJECTED")])
def test_review_terminal_version_and_reopen(setup, decision, status):
    _, repo, service, _, ai = setup
    run = start(service, repo, ai)
    args = dict(actor=actor(user="reviewer"), repository=repo, run_id=run["run_id"],
                decision=decision, draft_version=1, note="Synthetic review")
    with pytest.raises(RunConflict):
        service.review_pilot(**{**args, "draft_version": 2})
    reviewed = service.review_pilot(**args)
    assert reviewed["status"] == status
    assert reviewed["review"]["reviewer_id"] == "reviewer"
    assert reviewed["review"]["reviewed_at"]
    reopened = WorkforceRunRepository(repo.path)
    assert reopened.get(run["run_id"]) == reviewed
    assert service.review_pilot(**{**args, "repository": reopened}) == reviewed
    for change in ({"decision": "REJECT" if decision == "APPROVE" else "APPROVE"},
                   {"actor": actor(user="different")}, {"note": "changed"}, {"draft_version": 2}):
        with pytest.raises(RunConflict):
            service.review_pilot(**{**args, **change})
    with pytest.raises(RunConflict):
        repo.finish_execution(run["run_id"], result=None, elapsed_ms=0)


def test_all_providers_fail_without_draft_or_secret(setup):
    _, repo, service, provider, ai = setup
    provider.fail = True
    run = start(service, repo, ai)
    assert run["status"] == run["outcome"] == "FAILED"
    assert run["draft"] is None and run["actual_provider"] is None
    assert "sensitive exception" not in str(run)
    with pytest.raises(RunConflict):
        repo.review(run["run_id"], reviewer_id="r", decision="APPROVE", draft_version=1, note=None)
    assert start(service, repo, ai) == run
    assert provider.calls == 1


def test_concurrent_start_and_review(setup):
    _, repo, service, provider, ai = setup
    entered, release = Event(), Event()
    original = provider.generate

    def blocked(request):
        entered.set()
        assert release.wait(5)
        return original(request)

    provider.generate = blocked
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(start, service, repo, ai)
        assert entered.wait(5)
        try:
            duplicate = pool.submit(start, service, WorkforceRunRepository(repo.path), ai).result(5)
            assert duplicate["status"] == "RUNNING"
        finally:
            release.set()
        result = first.result(5)
        assert result["run_id"] == duplicate["run_id"] and provider.calls == 1
        def review(decision):
            try:
                return repo.review(result["run_id"], reviewer_id="r", decision=decision, draft_version=1, note=None)["status"]
            except RunConflict:
                return "CONFLICT"
        reviews = list(pool.map(review, ["APPROVE", "REJECT"]))
        assert reviews.count("CONFLICT") == 1


@pytest.mark.parametrize("action", ["start", "review", "read"])
@pytest.mark.parametrize("permission", [None, "none", "execute", "review"])
def test_api_auth(setup, action, permission):
    app, repo, service, _, ai = setup
    run = start(service, repo, ai)
    if permission is not None:
        app.dependency_overrides[deps.get_current_user] = lambda: actor(f"workforce.pilot.{permission}")
    client = TestClient(app)
    if action == "start":
        response = client.post("/api/workforce/pilot/runs", json={"idempotency_key": "api"})
    elif action == "review":
        response = client.post(f"/api/workforce/pilot/runs/{run['run_id']}/review",
                               json={"decision": "APPROVE", "draft_version": 1})
    else:
        response = client.get(f"/api/workforce/pilot/runs/{run['run_id']}")
    allowed = permission in ({"execute", "review"} if action == "read" else {"execute" if action == "start" else "review"})
    assert response.status_code == (401 if permission is None else 200 if allowed else 403)
    if action == "review" and allowed:
        assert response.json()["review"]["reviewer_id"] == "server-user"


@pytest.mark.parametrize("field,value", [("role", "SUPERUSER"), ("is_human", True), ("chief", True),
                                        ("reviewer", "attacker"), ("reviewer_id", "attacker"), ("username", "attacker")])
def test_spoofed_payload_forbidden(setup, field, value):
    app, repo, service, _, ai = setup
    run = start(service, repo, ai)
    client = TestClient(app)
    app.dependency_overrides[deps.get_current_user] = lambda: actor()
    body = {"decision": "APPROVE", "draft_version": 1, field: value}
    url = f"/api/workforce/pilot/runs/{run['run_id']}/review"
    assert client.post(url, json=body).status_code == 403
    app.dependency_overrides[deps.get_current_user] = lambda: actor("workforce.pilot.review", "workforce.pilot.execute")
    assert client.post(url, json=body).status_code == 422
    assert client.post("/api/workforce/pilot/runs", json={"idempotency_key": "spoof", field: value}).status_code == 422
    assert repo.get(run["run_id"])["review"] is None


def test_scope_and_input_boundary(setup):
    app, repo, service, provider, ai = setup
    run = start(service, repo, ai)
    app.dependency_overrides[deps.get_current_user] = lambda: actor("workforce.pilot.execute", "workforce.pilot.review", org="other")
    client = TestClient(app)
    assert client.get(f"/api/workforce/pilot/runs/{run['run_id']}").status_code == 404
    assert client.post(f"/api/workforce/pilot/runs/{run['run_id']}/review", json={"decision": "APPROVE", "draft_version": 1}).status_code == 404
    for body in ({"input_text": "arbitrary private text"}, {"mission_type": "OTHER"}, {"metadata": {"pilot": True}}):
        assert client.post("/api/workforce/pilot/runs", json={"idempotency_key": "invalid", **body}).status_code == 422
    with pytest.raises(ValueError):
        WorkforceTextExecutor(ai).execute(MISSION_TYPE, "private")
    assert provider.calls == 1


def test_structured_response_and_legacy():
    ai = EngineeringAIClient(Router())
    ai._router.register_provider(MockLLMProvider())
    response = ai.generate_response("synthetic")
    assert ai.generate("synthetic") == response.content
    assert response.provider and response.model and response.finish_reason


def test_isolated_factory_and_environment(monkeypatch):
    shared = deps.get_copilot_ai_client()
    selector = shared._router.provider_selector
    before_policy = selector._routing_policy
    monkeypatch.setenv("AI5R_ROUTING_POLICY", "LOCAL_FIRST")
    before_env = dict(os.environ)
    pilot = deps.get_workforce_pilot_ai_client()
    assert pilot is not shared and pilot._router is not shared._router
    assert pilot._router.provider_selector is not selector
    assert pilot._router.provider_selector._routing_policy.mode is RoutingMode.DAHONO_PRIMARY
    assert shared._router.provider_selector is selector and selector._routing_policy is before_policy
    assert dict(os.environ) == before_env
    assert deps._build_copilot_ai_client()._router.provider_selector._routing_policy.mode is RoutingMode.LOCAL_FIRST


def test_repository_configuration_is_explicit_and_nonproduction(monkeypatch, tmp_path):
    from fastapi import HTTPException
    monkeypatch.delenv("AI5R_WORKFORCE_PILOT_DB", raising=False)
    with pytest.raises(HTTPException):
        deps.get_workforce_run_repository()
    monkeypatch.setenv("AI5R_WORKFORCE_PILOT_DB", str(tmp_path / "pilot.db"))
    monkeypatch.setenv("AI5R_ENV", "production")
    with pytest.raises(HTTPException):
        deps.get_workforce_run_repository()


def test_interrupted_claim_survives_reopen_without_retry(setup):
    _, repo, service, provider, ai = setup
    run, created = repo.claim(organization_id="org", requester_id="server-user",
                              idempotency_key="key", mission_type=MISSION_TYPE,
                              employee={"position_id": "DOCUMENTATION_ENGINEER"},
                              requested_policy="DAHONO_PRIMARY")
    assert created
    assert start(service, WorkforceRunRepository(repo.path), ai) == run
    assert provider.calls == 0 and run["status"] == "RUNNING"
    with pytest.raises(RunConflict):
        repo.claim(organization_id="org", requester_id="other", idempotency_key="key",
                   mission_type=MISSION_TYPE, employee={}, requested_policy="DAHONO_PRIMARY")


@pytest.mark.parametrize("content", ["", "x" * 16001])
def test_invalid_output_fails_closed(setup, content):
    _, repo, service, provider, ai = setup
    provider.generate = lambda request: LLMResponse("DAHONO", "model", content, "stop")
    run = start(service, repo, ai)
    assert run["status"] == "FAILED" and run["draft"] is None


def test_api_stale_conflict_and_idempotent_review(setup):
    app, repo, service, provider, ai = setup
    app.dependency_overrides[deps.get_current_user] = lambda: actor("workforce.pilot.execute", "workforce.pilot.review")
    client = TestClient(app)
    run = client.post("/api/workforce/pilot/runs", json={"idempotency_key": "api"}).json()
    assert client.post("/api/workforce/pilot/runs", json={"idempotency_key": "api"}).json() == run
    assert provider.calls == 1
    url = f"/api/workforce/pilot/runs/{run['run_id']}/review"
    assert client.post(url, json={"decision": "APPROVE", "draft_version": 2}).status_code == 409
    body = {"decision": "APPROVE", "draft_version": 1}
    reviewed = client.post(url, json=body)
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "COMPLETED"
    assert client.post(url, json=body).json() == reviewed.json()
    assert client.post(url, json={"decision": "REJECT", "draft_version": 1}).status_code == 409
    assert provider.calls == 1
