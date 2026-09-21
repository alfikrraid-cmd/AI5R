from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
AI5R_SDK_DIR = CORE_SERVICES_DIR.parent / "AI5R-SDK"

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app
from dependencies import get_copilot_ai_client, get_live_stream_api, get_workforce_service
from API.workforce_service import WorkforceService


@pytest.fixture
def fresh_workforce_service():
    """Provides a fresh isolated WorkforceService for each test."""
    service = WorkforceService(organization_name="AI5R Test Enterprise")
    app.dependency_overrides[get_workforce_service] = lambda: service
    app.dependency_overrides[get_live_stream_api] = lambda: service.live_stream_api
    # Deterministic tests must never reach the configured live AI providers.
    app.dependency_overrides[get_copilot_ai_client] = lambda: None
    yield service
    app.dependency_overrides.pop(get_workforce_service, None)
    app.dependency_overrides.pop(get_live_stream_api, None)
    app.dependency_overrides.pop(get_copilot_ai_client, None)



@pytest.fixture
def client(fresh_workforce_service):
    return TestClient(app)


def test_list_employees(client):
    response = client.get("/api/workforce/employees")
    assert response.status_code == 200
    employees = response.json()
    assert len(employees) == 9

    positions = {e["position_id"] for e in employees}
    assert "CTO" in positions
    assert "PROJECT_MANAGER" in positions
    assert "SOLUTION_ARCHITECT" in positions
    assert "BACKEND_ENGINEER" in positions
    assert "FRONTEND_ENGINEER" in positions
    assert "QA_ENGINEER" in positions
    assert "DEVOPS_ENGINEER" in positions
    assert "SECURITY_ENGINEER" in positions
    assert "DOCUMENTATION_ENGINEER" in positions

    for emp in employees:
        assert emp["employee_id"].startswith("EMP-")
        assert emp["employee_name"]
        assert emp["role"]
        assert emp["status"] in ("AVAILABLE", "WORKING", "WAITING_APPROVAL", "OFFLINE")
        assert isinstance(emp["skills"], list)
        assert len(emp["skills"]) > 0
        assert "avatar" in emp


def test_get_employee_by_id_and_position(client, fresh_workforce_service):
    employees = fresh_workforce_service.employees
    target = employees[0]

    # By employee_id
    res1 = client.get(f"/api/workforce/employees/{target.employee_id}")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["employee_id"] == target.employee_id
    assert data1["position_id"] == target.position_id
    assert "activities" in data1

    # By position_id
    res2 = client.get("/api/workforce/employees/CTO")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["position_id"] == "CTO"


def test_get_employee_not_found(client):
    response = client.get("/api/workforce/employees/NON_EXISTENT_ID_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_board(client):
    response = client.get("/api/workforce/board")
    assert response.status_code == 200
    board = response.json()
    assert "published" in board
    assert "claimed" in board
    assert "completed" in board
    assert "released" in board
    assert "summary" in board
    assert board["summary"]["total_items"] == 0


def test_get_activities(client, fresh_workforce_service):
    res_empty = client.get("/api/workforce/activities")
    assert res_empty.status_code == 200
    assert isinstance(res_empty.json(), list)

    # Assign a task to generate an activity
    client.post(
        "/api/workforce/tasks/assign",
        json={
            "title": "Build Test Module",
            "position_id": "BACKEND_ENGINEER",
        },
    )

    res_acts = client.get("/api/workforce/activities?limit=10")
    assert res_acts.status_code == 200
    acts = res_acts.json()
    assert len(acts) >= 1
    assert acts[0]["activity_type"] in ("RECEIVED_WORK", "EMPLOYEE_ACTIVITY_RECORDED")


def test_get_metrics(client):
    response = client.get("/api/workforce/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["status"] == "OK"
    assert metrics["total_employees"] == 9
    assert metrics["active_employees"] == 9
    assert metrics["uptime"] == "OPERATIONAL"
    assert metrics["total_tasks"] == 0
    assert metrics["pending_approvals"] == 0


def test_assign_task_success(client):
    payload = {
        "title": "Implement Notification Dispatcher",
        "description": "Send alerts via webhook",
        "position_id": "BACKEND_ENGINEER",
        "is_production": False,
        "metadata": {"sprint": "SPRINT-01"},
    }
    response = client.post("/api/workforce/tasks/assign", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ASSIGNED"
    work_item = data["work_item"]
    assert work_item["title"] == "Implement Notification Dispatcher"
    assert work_item["assigned_position_id"] == "BACKEND_ENGINEER"
    assert work_item["assigned_employee_id"] is not None
    assert work_item["status"] == "CLAIMED"
    assert work_item["is_production"] is False


def test_assign_task_validation(client):
    # Empty title
    res_bad = client.post("/api/workforce/tasks/assign", json={"title": "  "})
    assert res_bad.status_code == 400

    # Non-existent employee ID
    res_emp = client.post(
        "/api/workforce/tasks/assign",
        json={"title": "Task", "employee_id": "EMP-NON-EXISTENT"},
    )
    assert res_emp.status_code == 404


def test_chief_approval_gate_enforcement_via_api(client, fresh_workforce_service):
    """Verifies that production tasks cannot be released without human Chief approval."""
    # 1. Assign production task
    assign_res = client.post(
        "/api/workforce/tasks/assign",
        json={
            "title": "Deploy Core Kernel Upgrade to Production",
            "position_id": "DEVOPS_ENGINEER",
            "is_production": True,
        },
    )
    assert assign_res.status_code == 200
    work_item_id = assign_res.json()["work_item"]["work_item_id"]

    # 2. Advance to COMPLETED status on board
    devops_emp = fresh_workforce_service.find_employee_by_position("DEVOPS_ENGINEER")
    fresh_workforce_service.work_board.complete(devops_emp, work_item_id)

    # 3. Verify metrics reflect pending Chief approval
    metrics_res = client.get("/api/workforce/metrics")
    assert metrics_res.json()["pending_approvals"] == 1

    # 4. Attempt release WITHOUT approval -> MUST FAIL CLOSED (403)
    release_attempt_1 = client.post(f"/api/workforce/tasks/{work_item_id}/release", json={})
    assert release_attempt_1.status_code == 403
    assert "Chief approval" in release_attempt_1.json()["detail"]

    # 5. Attempt release with non-human / AI employee approval -> MUST FAIL CLOSED (403)
    release_attempt_2 = client.post(
        f"/api/workforce/tasks/{work_item_id}/release",
        json={
            "approver_id": "EMP-AI-CTO",
            "approver_role": "CHIEF",
            "is_human": False,  # Non-human!
        },
    )
    assert release_attempt_2.status_code == 403
    assert "human" in release_attempt_2.json()["detail"].lower()

    # 6. Release WITH valid human Chief approval -> SUCCEEDS (200)
    release_success = client.post(
        f"/api/workforce/tasks/{work_item_id}/release",
        json={
            "approver_id": "CHIEF-USER-01",
            "approver_role": "CHIEF",
            "is_human": True,
        },
    )
    assert release_success.status_code == 200
    data = release_success.json()
    assert data["status"] == "RELEASED"
    assert data["work_item"]["status"] == "RELEASED"

    # 7. Metrics reflect 0 pending approvals and 1 released task
    metrics_after = client.get("/api/workforce/metrics").json()
    assert metrics_after["pending_approvals"] == 0
    assert metrics_after["released_tasks"] == 1


def test_workforce_chat_deterministic_fallback(client):
    payload = {
        "employee_id": "BACKEND_ENGINEER",
        "message": "Please review the SQL indexes.",
    }
    response = client.post("/api/workforce/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["conversation_id"].startswith("CONV-")
    assert "BACKEND_ENGINEER" in data["response"] or "AI Backend Engineer" in data["response"]
    assert len(data["messages"]) == 2  # user + assistant

    # Multi-turn conversation continuation
    conv_id = data["conversation_id"]
    response2 = client.post(
        "/api/workforce/chat",
        json={
            "employee_id": "BACKEND_ENGINEER",
            "message": "Focus on the condition_monitoring table.",
            "conversation_id": conv_id,
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["conversation_id"] == conv_id
    assert len(data2["messages"]) == 4


def test_workforce_chat_with_ai_client(client):
    mock_ai_client = MagicMock()
    mock_ai_client.generate.return_value = "I have reviewed the architecture and recommend partitioning."

    app.dependency_overrides[get_copilot_ai_client] = lambda: mock_ai_client
    try:
        response = client.post(
            "/api/workforce/chat",
            json={
                "employee_id": "CTO",
                "message": "What is the partitioning strategy?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "I have reviewed the architecture and recommend partitioning."
        assert mock_ai_client.generate.called
    finally:
        app.dependency_overrides.pop(get_copilot_ai_client, None)


def test_studio_events_stream_sse(client, fresh_workforce_service):
    # Publish an event to the live stream
    fresh_workforce_service.live_stream_api.publish(
        event_type="WORKFORCE_READY",
        payload={"system": "AI5R Digital Workforce", "status": "ONLINE"},
    )

    # Request SSE snapshot stream (follow=false for bounded read)
    response = client.get("/api/studio/events/stream?follow=false")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "event: WORKFORCE_READY" in text
    assert "ONLINE" in text
