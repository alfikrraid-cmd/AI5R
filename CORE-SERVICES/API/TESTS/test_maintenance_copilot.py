import sys
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.maintenance_copilot import (
    explain_assigned_role,
    explain_pump_history,
    explain_pump_status,
    explain_work_orders,
    show_pump,
    summarize_maintenance_situation,
)


def test_show_pump_formats_found_pump():
    status = {
        "success": True,
        "message": "Pump detail found",
        "data": {"tag_number": "P-101", "pump_type": "Centrifugal", "status": "ACTIVE"},
    }

    with patch("API.maintenance_copilot.get_pump_status", return_value=status) as mock_status:
        result = show_pump("P-101")

    mock_status.assert_called_once_with("P-101")
    assert result["message"] == "Pump P-101 (Centrifugal) — status: ACTIVE."
    assert result["data"] == status


def test_show_pump_formats_not_found_pump():
    status = {"success": False, "message": "Pump not found", "data": None}

    with patch("API.maintenance_copilot.get_pump_status", return_value=status):
        result = show_pump("UNKNOWN")

    assert result["message"] == "Pump UNKNOWN was not found."
    assert result["data"] == status


def test_explain_pump_status_includes_location_and_area():
    status = {
        "success": True,
        "message": "found",
        "data": {"tag_number": "P-101", "status": "ACTIVE", "location": "Unit 1", "area": "North"},
    }

    with patch("API.maintenance_copilot.get_pump_status", return_value=status):
        result = explain_pump_status("P-101")

    assert result["message"] == (
        "Pump P-101 is currently ACTIVE, located at Unit 1 in area North."
    )


def test_explain_pump_history_lists_records():
    history = {
        "success": True,
        "tag_number": "P-101",
        "records": [
            {
                "maintenance_record_code": "MH-101",
                "action_taken": "Replaced bearing",
                "performed_by": "Field Technician",
                "performed_at": "2026-07-14T09:00:00.000Z",
            }
        ],
    }

    with patch("API.maintenance_copilot.get_pump_history", return_value=history):
        result = explain_pump_history("P-101")

    assert "Pump P-101 has 1 maintenance record(s):" in result["message"]
    assert "MH-101: Replaced bearing by Field Technician on 2026-07-14T09:00:00.000Z" in result["message"]


def test_explain_pump_history_handles_empty():
    history = {"success": True, "tag_number": "P-101", "records": []}

    with patch("API.maintenance_copilot.get_pump_history", return_value=history):
        result = explain_pump_history("P-101")

    assert result["message"] == "No maintenance history found for pump P-101."


def test_explain_work_orders_lists_active_orders():
    active = {
        "success": True,
        "work_orders": [
            {"work_order_code": "WO-101", "status": "OPEN", "assigned_to": "Field Technician"}
        ],
    }

    with patch("API.maintenance_copilot.get_active_work_orders", return_value=active) as mock_active:
        result = explain_work_orders("P-101")

    mock_active.assert_called_once_with("P-101")
    assert "1 active work order(s) for pump P-101:" in result["message"]
    assert "WO-101: OPEN (assigned to Field Technician)" in result["message"]


def test_explain_work_orders_handles_no_orders():
    active = {"success": True, "work_orders": []}

    with patch("API.maintenance_copilot.get_active_work_orders", return_value=active):
        result = explain_work_orders()

    assert result["message"] == "No active work orders."


def test_explain_assigned_role_formats_role():
    role = {
        "role": {"name": "Field Technician"},
        "relationships": {"department": "Field Operations"},
    }

    with patch("API.maintenance_copilot.get_assigned_role", return_value=role) as mock_role:
        result = explain_assigned_role("LTSA-BRAIN", "WO-101", root_path="/tmp/fake")

    mock_role.assert_called_once_with("LTSA-BRAIN", "WO-101", root_path="/tmp/fake")
    assert result["message"] == (
        "Work order WO-101 is assigned to Field Technician in Field Operations."
    )


def test_explain_assigned_role_handles_no_role():
    with patch("API.maintenance_copilot.get_assigned_role", return_value=None):
        result = explain_assigned_role("LTSA-BRAIN", "WO-101")

    assert result["message"] == "Work order WO-101 has no role assigned."


def test_summarize_maintenance_situation_formats_summary():
    situation = {
        "summary": {
            "total_pumps": 2,
            "active_work_orders": 1,
            "completed_today": 1,
            "overdue_work_orders": 0,
        },
        "recent_work_orders": [],
        "recent_maintenance": [],
        "organization_summary": {"departments": 1, "roles": 1},
    }

    with patch("API.maintenance_copilot.summarize_situation", return_value=situation):
        result = summarize_maintenance_situation("LTSA-BRAIN")

    assert result["message"] == (
        "2 pump(s) tracked, 1 active work order(s), 1 maintenance record(s) completed today, "
        "0 overdue work order(s)."
    )
    assert result["data"] == situation
