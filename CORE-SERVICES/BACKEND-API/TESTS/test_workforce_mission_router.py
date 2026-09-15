import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parent.parent
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
REPO_ROOT = CORE_SERVICES_DIR.parent
AI5R_SDK_DIR = REPO_ROOT / "AI5R-SDK"

for p in (str(BACKEND_API_DIR), str(CORE_SERVICES_DIR), str(AI5R_SDK_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from API.STREAMING.live_stream_api import LiveStreamAPI
from API.workforce_service import WorkforceService
from dependencies import (
    get_copilot_ai_client,
    get_live_stream_api,
    get_workforce_service,
)
from routers.workforce import router as workforce_router


def create_test_client() -> tuple[TestClient, WorkforceService, LiveStreamAPI]:
    app = FastAPI()
    app.include_router(workforce_router)

    live_api = LiveStreamAPI()
    service = WorkforceService(
        organization_name="AI5R Test Enterprise",
        live_stream_api=live_api,
    )

    app.dependency_overrides[get_workforce_service] = lambda: service
    app.dependency_overrides[get_live_stream_api] = lambda: live_api

    client = TestClient(app)
    return client, service, live_api


def test_create_mission_validation():
    client, _, _ = create_test_client()
    res = client.post("/api/workforce/missions", json={"title": "   "})
    assert res.status_code == 400


def test_create_mission_decomposition_and_assignment():
    client, service, _ = create_test_client()
    payload = {
        "title": "Build Customer Portal Auth",
        "description": "Implement OAuth2 and passkey authentication",
        "is_production": False,
    }
    res = client.post("/api/workforce/missions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "MISSION_CREATED"
    mission = data["mission"]
    assert mission["title"] == "Build Customer Portal Auth"
    assert mission["status"] == "IN_PROGRESS"
    assert mission["progress"] == 0

    tasks = mission["tasks"]
    assert len(tasks) == 6
    positions = [t["assigned_position_id"] for t in tasks]
    assert "SOLUTION_ARCHITECT" in positions
    assert "BACKEND_ENGINEER" in positions
    assert "FRONTEND_ENGINEER" in positions
    assert "QA_ENGINEER" in positions
    assert "DEVOPS_ENGINEER" in positions
    assert "DOCUMENTATION_ENGINEER" in positions

    # Verify all tasks are assigned to active employees
    for t in tasks:
        assert t["assigned_employee_id"] is not None
        assert t["assigned_employee_name"] is not None

    # Verify execution plan dependency graph
    plan = mission["execution_plan"]
    assert plan is not None
    graph = plan["dependency_graph"]
    tasks_by_pos = {t["assigned_position_id"]: t for t in tasks}
    arch_id = tasks_by_pos["SOLUTION_ARCHITECT"]["work_item_id"]
    be_id = tasks_by_pos["BACKEND_ENGINEER"]["work_item_id"]
    fe_id = tasks_by_pos["FRONTEND_ENGINEER"]["work_item_id"]
    qa_id = tasks_by_pos["QA_ENGINEER"]["work_item_id"]
    devops_id = tasks_by_pos["DEVOPS_ENGINEER"]["work_item_id"]

    assert graph[arch_id] == []
    assert arch_id in graph[be_id]
    assert arch_id in graph[fe_id]
    assert be_id in graph[qa_id]
    assert fe_id in graph[qa_id]
    assert qa_id in graph[devops_id]

    # Verify initial task is running
    assert arch_id in plan["running"]


def test_list_and_get_missions():
    client, _, _ = create_test_client()
    res1 = client.post("/api/workforce/missions", json={"title": "Mission Alpha"})
    assert res1.status_code == 200
    mission_id = res1.json()["mission"]["mission_id"]

    # List missions
    res_list = client.get("/api/workforce/missions")
    assert res_list.status_code == 200
    missions = res_list.json()
    assert len(missions) == 1
    assert missions[0]["mission_id"] == mission_id

    # Get single mission
    res_get = client.get(f"/api/workforce/missions/{mission_id}")
    assert res_get.status_code == 200
    assert res_get.json()["mission_id"] == mission_id

    # 404 for missing mission
    res_missing = client.get("/api/workforce/missions/non-existent-id")
    assert res_missing.status_code == 404


def test_mission_board_and_activity_integration():
    client, service, _ = create_test_client()
    res = client.post("/api/workforce/missions", json={"title": "Mission Beta"})
    assert res.status_code == 200
    mission = res.json()["mission"]
    tasks = mission["tasks"]

    # Check board integration
    board_res = client.get("/api/workforce/board")
    assert board_res.status_code == 200
    board = board_res.json()
    assert board["summary"]["total_items"] >= 6
    claimed = board["claimed"]
    published = board["published"]
    claimed_ids = [c["work_item_id"] for c in claimed]
    published_ids = [p["work_item_id"] for p in published]

    tasks_by_pos = {t["assigned_position_id"]: t for t in tasks}
    arch_id = tasks_by_pos["SOLUTION_ARCHITECT"]["work_item_id"]
    be_id = tasks_by_pos["BACKEND_ENGINEER"]["work_item_id"]

    assert arch_id in claimed_ids
    assert be_id in published_ids

    # Check activity feed integration (NEXA activity recorded)
    act_res = client.get("/api/workforce/activities")
    assert act_res.status_code == 200
    activities = act_res.json()
    delegated_acts = [a for a in activities if a["activity_type"] == "MISSION_DELEGATED"]
    assert len(delegated_acts) >= 1
    assert delegated_acts[0]["mission_id"] == mission["mission_id"]


def test_production_mission_chief_approval_gate():
    client, service, _ = create_test_client()
    res = client.post(
        "/api/workforce/missions",
        json={"title": "Production Deployment Mission", "is_production": True},
    )
    assert res.status_code == 200
    mission = res.json()["mission"]
    tasks_by_pos = {t["assigned_position_id"]: t for t in mission["tasks"]}
    devops_task = tasks_by_pos["DEVOPS_ENGINEER"]
    assert devops_task["is_production"] is True

    # Complete the devops task manually to test release gate
    devops_item_id = devops_task["work_item_id"]
    devops_emp = service.find_employee(devops_task["assigned_employee_id"])

    # First claim it
    if devops_item_id in service.work_board._published:
        service.work_board.claim(devops_emp, devops_item_id)
    service.work_board.complete(devops_emp, devops_item_id)

    # Attempt release without Chief approval -> blocked with 403
    fail_res = client.post(f"/api/workforce/tasks/{devops_item_id}/release", json={})
    assert fail_res.status_code == 403

    # Attempt release with AI approval (not human) -> blocked with 403
    ai_fail = client.post(
        f"/api/workforce/tasks/{devops_item_id}/release",
        json={
            "approver_id": "ID-PROJECT_MANAGER",
            "approver_role": "PROJECT_MANAGER",
            "is_human": False,
        },
    )
    assert ai_fail.status_code == 403

    # Release with valid Human Chief approval -> 200 success
    success_res = client.post(
        f"/api/workforce/tasks/{devops_item_id}/release",
        json={
            "approver_id": "raid",
            "approver_role": "CHIEF_ARCHITECT",
            "is_human": True,
        },
    )
    assert success_res.status_code == 200
    assert success_res.json()["status"] == "RELEASED"
