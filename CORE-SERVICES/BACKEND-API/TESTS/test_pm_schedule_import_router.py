"""AI5R-PHASE4E4 -- POST /api/ltsa/pm-schedules/import/parse and
GET /api/ltsa/pm-schedules/import/template: maintenance.write
authorization (same reasoning as the bulk-create route), non-.xlsx
rejection, and that a structural parse failure surfaces as one readable
422, never a raw traceback."""

import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


def _override(role: str):
    app.dependency_overrides[get_current_user] = lambda: _identity(role)


def _xlsx_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def setup_function():
    app.dependency_overrides.clear()


def teardown_function():
    app.dependency_overrides.clear()


# --- parse --------------------------------------------------------------


def test_tap_engineer_with_maintenance_write_can_parse():
    _override("TAP_ENGINEER")
    data = _xlsx_bytes([("Pump Tag", "Frequency"), ("211-P-1A", "MONTHLY")])

    response = client.post(
        "/api/ltsa/pm-schedules/import/parse",
        files={"file": ("schedules.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["headers"] == ["Pump Tag", "Frequency"]
    assert body["rows"] == [["211-P-1A", "MONTHLY"]]


def test_pertamina_viewer_cannot_parse():
    _override("PERTAMINA_VIEWER")
    data = _xlsx_bytes([("Pump Tag",), ("211-P-1A",)])

    response = client.post(
        "/api/ltsa/pm-schedules/import/parse",
        files={"file": ("schedules.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 403


def test_anonymous_parse_is_401():
    data = _xlsx_bytes([("Pump Tag",), ("211-P-1A",)])
    response = client.post(
        "/api/ltsa/pm-schedules/import/parse",
        files={"file": ("schedules.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 401


def test_non_xlsx_extension_is_rejected_before_parsing():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-schedules/import/parse",
        files={"file": ("schedules.csv", b"Pump Tag,Frequency\n211-P-1A,MONTHLY", "text/csv")},
    )
    assert response.status_code == 422
    assert ".xlsx" in response.json()["detail"]


def test_structural_parse_failure_is_one_readable_422_never_a_crash():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-schedules/import/parse",
        files={"file": ("schedules.xlsx", b"not a real workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "object Object" not in response.text


# --- template -------------------------------------------------------------


def test_tap_engineer_can_download_template():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/pm-schedules/import/template")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 0


def test_pertamina_viewer_cannot_download_template():
    _override("PERTAMINA_VIEWER")
    response = client.get("/api/ltsa/pm-schedules/import/template")
    assert response.status_code == 403
