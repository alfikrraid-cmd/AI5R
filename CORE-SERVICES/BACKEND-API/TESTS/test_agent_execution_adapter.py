import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

BACKEND_API_DIR = Path(__file__).resolve().parent.parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for p in (str(BACKEND_API_DIR), str(CORE_SERVICES_DIR), str(AI5R_SDK_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from API.STREAMING.live_stream_api import LiveStreamAPI
from API.agent_execution_adapter import AgentExecutionAdapter, ExecutionArtifact
from API.workforce_service import WorkforceService
from dependencies import (
    get_copilot_ai_client,
    get_live_stream_api,
    get_workforce_service,
)
from routers.workforce import router as workforce_router
from WORKFORCE.approval_chain_runtime import ChiefApprovalRequiredError
from WORKFORCE.work_item import WorkItem


class MockAIClient:
    def __init__(self, response_text: str | None = None, should_fail: bool = False, fail_msg: str = "LLM unavailable"):
        self.should_fail = should_fail
        self.fail_msg = fail_msg
        self.calls: list[dict[str, Any]] = []
        self._default_provider = "mock-claude"
        self._response_text = response_text or json.dumps({
            "summary": "Completed architectural and system analysis.",
            "findings": ["Decoupled microservice pattern recommended", "Token-based auth with refresh flow"],
            "deliverables": "Proposed schema design and endpoint specifications.",
            "risks_and_considerations": ["Network latency between services", "Token expiration window"]
        })

    def generate(self, prompt: str, *, system_prompt: str = "", temperature: float = 0.2, capability: str = "chat", metadata: dict | None = None) -> str:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "capability": capability,
            "metadata": metadata,
        })
        if self.should_fail:
            raise RuntimeError(self.fail_msg)
        return self._response_text


def setup_test_env(ai_client: MockAIClient | None = None) -> tuple[TestClient, WorkforceService, LiveStreamAPI, MockAIClient]:
    app = FastAPI()
    app.include_router(workforce_router)

    live_api = LiveStreamAPI()
    service = WorkforceService(
        organization_name="AI5R Test Enterprise",
        live_stream_api=live_api,
    )
    mock_ai = ai_client or MockAIClient()

    app.dependency_overrides[get_workforce_service] = lambda: service
    app.dependency_overrides[get_live_stream_api] = lambda: live_api
    app.dependency_overrides[get_copilot_ai_client] = lambda: mock_ai

    client = TestClient(app)
    return client, service, live_api, mock_ai


# 1. Claimed WorkItem executes
def test_1_claimed_work_item_executes():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Design Auth Subsystem",
        description="Specify OAuth2 tokens and session flow",
        position_id="SOLUTION_ARCHITECT",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["artifact"]["status"] == "SUCCESS"
    assert "summary" in data["artifact"]


# 2. Canonical employee used
def test_2_canonical_employee_used():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Design Auth Subsystem",
        position_id="SOLUTION_ARCHITECT",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    assigned_emp_id = assign_res["work_item"]["assigned_employee_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 200
    artifact = res.json()["artifact"]
    assert artifact["employee_id"] == assigned_emp_id
    assert artifact["role"] == "SOLUTION_ARCHITECT"


# 3. EngineeringAIClient invoked
def test_3_engineering_ai_client_invoked():
    mock_ai = MockAIClient()
    client, service, _, _ = setup_test_env(mock_ai)
    assign_res = service.assign_task(
        title="Implement Rate Limiting",
        description="Token bucket in Redis",
        position_id="BACKEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 200
    assert len(mock_ai.calls) == 1
    call = mock_ai.calls[0]
    assert "Implement Rate Limiting" in call["prompt"]
    assert "BACKEND_ENGINEER" in call["system_prompt"]


# 4. Structured artifact created
def test_4_structured_artifact_created():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Draft Architecture Spec",
        position_id="SOLUTION_ARCHITECT",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    artifact = res.json()["artifact"]
    assert artifact["artifact_id"].startswith("ART-")
    assert artifact["work_item_id"] == work_item_id
    assert artifact["status"] == "SUCCESS"
    assert artifact["started_at"]
    assert artifact["completed_at"]
    assert "findings" in artifact["output"]
    assert "deliverables" in artifact["output"]
    assert "risks_and_considerations" in artifact["output"]


# 5. Successful artifact completes WorkItem
def test_5_successful_artifact_completes_work_item():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Analyze UI Architecture",
        position_id="FRONTEND_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    item = service.find_work_item(work_item_id)
    assert item.status == "COMPLETED"
    assert item.artifact_id is not None
    assert item.work_item_id in [c.work_item_id for c in service.work_board.completed_work_items()]


# 6. Provider failure does not complete
def test_6_provider_failure_does_not_complete():
    mock_ai = MockAIClient(should_fail=True, fail_msg="OpenAI API rate limit exceeded")
    client, service, _, _ = setup_test_env(mock_ai)
    assign_res = service.assign_task(
        title="Analyze Security Posture",
        position_id="SECURITY_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 502

    # Verify task remains CLAIMED and NOT completed
    item = service.find_work_item(work_item_id)
    assert item.status == "CLAIMED"
    assert item.work_item_id in [c.work_item_id for c in service.work_board.claimed_work_items()]
    assert item.work_item_id not in [c.work_item_id for c in service.work_board.completed_work_items()]


# 7. Malformed response does not complete
def test_7_malformed_response_does_not_complete():
    mock_ai = MockAIClient(response_text="Not valid JSON at all")
    client, service, _, _ = setup_test_env(mock_ai)
    assign_res = service.assign_task(
        title="Analyze Network Topology",
        position_id="DEVOPS_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 502

    item = service.find_work_item(work_item_id)
    assert item.status == "CLAIMED"


# 8. Duplicate execute prevented
def test_8_duplicate_execute_prevented():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Design API Gateway",
        position_id="SOLUTION_ARCHITECT",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res1 = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res1.status_code == 200

    res2 = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res2.status_code == 400
    assert "already" in res2.json()["detail"].lower()


# 9. Completed task cannot re-execute
def test_9_completed_task_cannot_reexecute():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Build Observability Plan",
        position_id="DEVOPS_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    emp = service.find_employee_by_position("DEVOPS_ENGINEER")
    service.work_board.complete(emp, work_item_id)

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 400
    assert "already" in res.json()["detail"].lower()


# 10. Unknown task rejected
def test_10_unknown_task_rejected():
    client, _, _, _ = setup_test_env()
    res = client.post("/api/workforce/tasks/WORK-NONEXISTENT-9999/execute")
    assert res.status_code == 404


# 11. Unclaimed task rejected
def test_11_unclaimed_task_rejected():
    client, service, _, _ = setup_test_env()
    raw_item = WorkItem(title="Unclaimed Work Item", assigned_position_id="SOLUTION_ARCHITECT")
    service.work_board.publish(raw_item)

    res = client.post(f"/api/workforce/tasks/{raw_item.work_item_id}/execute")
    assert res.status_code == 400
    assert "must be CLAIMED" in res.json()["detail"]


# 12. Dependency artifact passed to child
def test_12_dependency_artifact_passed_to_child():
    mock_ai = MockAIClient()
    client, service, _, _ = setup_test_env(mock_ai)

    mission = service.create_mission(
        title="Platform Migration",
        description="Migrate API to microservices",
    )
    mission_id = mission["mission_id"]
    tasks = mission["tasks"]
    arch_task = next(t for t in tasks if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    backend_task = next(t for t in tasks if t["assigned_position_id"] == "BACKEND_ENGINEER")

    # Step 1: Execute ARCH task
    arch_res = client.post(f"/api/workforce/tasks/{arch_task['work_item_id']}/execute")
    assert arch_res.status_code == 200
    arch_art = arch_res.json()["artifact"]

    # Step 2: Now backend task has been unblocked and claimed by scheduler
    assert service.find_work_item(backend_task["work_item_id"]).status == "CLAIMED"

    # Step 3: Execute BACKEND task
    backend_res = client.post(f"/api/workforce/tasks/{backend_task['work_item_id']}/execute")
    assert backend_res.status_code == 200

    # Inspect the backend call prompt: must contain ARCH artifact
    backend_call = mock_ai.calls[-1]
    assert "UPSTREAM DEPENDENCY ARTIFACTS" in backend_call["prompt"]
    assert arch_art["artifact_id"] in backend_call["prompt"]
    assert "SOLUTION_ARCHITECT" in backend_call["prompt"]


# 13. Unrelated artifact not leaked
def test_13_unrelated_artifact_not_leaked():
    mock_ai = MockAIClient()
    client, service, _, _ = setup_test_env(mock_ai)

    # Create standalone unrelated task and execute it
    unrelated_res = service.assign_task(
        title="Unrelated Legacy Audit",
        position_id="SECURITY_ENGINEER",
    )
    unrelated_id = unrelated_res["work_item"]["work_item_id"]
    client.post(f"/api/workforce/tasks/{unrelated_id}/execute")

    # Create a new mission
    mission = service.create_mission(title="Independent Project")
    arch_task = next(t for t in mission["tasks"] if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    client.post(f"/api/workforce/tasks/{arch_task['work_item_id']}/execute")

    arch_call = mock_ai.calls[-1]
    assert "Unrelated Legacy Audit" not in arch_call["prompt"]
    assert unrelated_id not in arch_call["prompt"]


# 14. SENTRY review receives parent artifacts & truthfulness enforcement
def test_14_sentry_qa_review_receives_parent_artifacts_and_truthfulness():
    mock_ai = MockAIClient()
    client, service, _, _ = setup_test_env(mock_ai)

    mission = service.create_mission(title="E-Commerce Checkout Pipeline")
    tasks = mission["tasks"]
    arch_task = next(t for t in tasks if t["assigned_position_id"] == "SOLUTION_ARCHITECT")
    backend_task = next(t for t in tasks if t["assigned_position_id"] == "BACKEND_ENGINEER")
    frontend_task = next(t for t in tasks if t["assigned_position_id"] == "FRONTEND_ENGINEER")
    qa_task = next(t for t in tasks if t["assigned_position_id"] == "QA_ENGINEER")

    # Execute ARCH
    client.post(f"/api/workforce/tasks/{arch_task['work_item_id']}/execute")
    # Execute BACKEND and FRONTEND
    client.post(f"/api/workforce/tasks/{backend_task['work_item_id']}/execute")
    client.post(f"/api/workforce/tasks/{frontend_task['work_item_id']}/execute")

    # Now QA task is unblocked and claimed
    qa_item = service.find_work_item(qa_task["work_item_id"])
    assert qa_item.status == "CLAIMED"

    # Execute QA
    res = client.post(f"/api/workforce/tasks/{qa_task['work_item_id']}/execute")
    assert res.status_code == 200

    qa_call = mock_ai.calls[-1]
    # SENTRY receives parent artifacts (backend, frontend)
    assert "UPSTREAM DEPENDENCY ARTIFACTS" in qa_call["prompt"]
    assert "BACKEND_ENGINEER" in qa_call["prompt"]
    assert "FRONTEND_ENGINEER" in qa_call["prompt"]
    # Verify truthfulness rule in system prompt
    assert "MUST NOT claim tests passed or failed unless real test execution evidence was supplied" in qa_call["system_prompt"]


# 15. Activity emitted
def test_15_activity_emitted():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Audit Cloud IAM Roles",
        position_id="SECURITY_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    client.post(f"/api/workforce/tasks/{work_item_id}/execute")

    activities = service.activity_registry.list_all()
    types = [a.activity_type for a in activities]
    assert "EXECUTION_STARTED" in types
    assert "ARTIFACT_CREATED" in types


# 16. SSE-compatible event emitted
def test_16_sse_compatible_event_emitted():
    client, service, live_api, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Produce Operations Runbook",
        position_id="DOCUMENTATION_ENGINEER",
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    client.post(f"/api/workforce/tasks/{work_item_id}/execute")

    events = live_api.latest()["events"]
    event_types = [e["event_type"] for e in events]
    assert "WORKFORCE_TASK_EXECUTING" in event_types
    assert "WORKFORCE_ARTIFACT_CREATED" in event_types
    assert "WORKFORCE_TASK_COMPLETED" in event_types


# 17. Production execution does not release
def test_17_production_execution_does_not_release():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Deploy Critical Hotfix",
        position_id="DEVOPS_ENGINEER",
        is_production=True,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]

    res = client.post(f"/api/workforce/tasks/{work_item_id}/execute")
    assert res.status_code == 200

    item = service.find_work_item(work_item_id)
    assert item.status == "COMPLETED"
    assert item.status != "RELEASED"
    assert item.metadata.get("is_production") is True


# 18. AI cannot approve
def test_18_ai_cannot_approve():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Deploy Critical Hotfix",
        position_id="DEVOPS_ENGINEER",
        is_production=True,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    client.post(f"/api/workforce/tasks/{work_item_id}/execute")

    # Attempt AI self-approval
    release_res = client.post(
        f"/api/workforce/tasks/{work_item_id}/release",
        json={
            "approver_id": "EMP-DEVOPS-001",
            "approver_role": "DEVOPS_ENGINEER",
            "is_human": False,
        },
    )
    assert release_res.status_code == 403
    item = service.find_work_item(work_item_id)
    assert item.status == "COMPLETED"
    assert item.status != "RELEASED"


# 19. Chief Gate remains fail-closed
def test_19_chief_gate_remains_fail_closed():
    client, service, _, _ = setup_test_env()
    assign_res = service.assign_task(
        title="Deploy Payment Gateway",
        position_id="DEVOPS_ENGINEER",
        is_production=True,
    )
    work_item_id = assign_res["work_item"]["work_item_id"]
    client.post(f"/api/workforce/tasks/{work_item_id}/execute")

    # 1. Release without approval returns 403
    fail_res = client.post(f"/api/workforce/tasks/{work_item_id}/release", json={})
    assert fail_res.status_code == 403

    # 2. Release with valid Human Chief approval succeeds
    ok_res = client.post(
        f"/api/workforce/tasks/{work_item_id}/release",
        json={
            "approver_id": "CHIEF-USER-01",
            "approver_role": "CHIEF",
            "is_human": True,
        },
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["status"] == "RELEASED"


# 20. No shell/filesystem/git execution introduced
def test_20_no_shell_filesystem_git_execution():
    adapter_file = CORE_SERVICES_DIR / "API" / "agent_execution_adapter.py"
    source = adapter_file.read_text(encoding="utf-8")

    forbidden_tokens = [
        "subprocess",
        "os.system",
        "os.popen",
        "os.spawn",
        "shutil.rmtree",
        "git push",
        "git commit",
        "popen",
        "shell=True",
        "write_bytes",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"Forbidden execution token '{token}' found in AgentExecutionAdapter!"
