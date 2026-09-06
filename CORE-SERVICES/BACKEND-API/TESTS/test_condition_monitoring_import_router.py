"""MWO-LTSA-CMON-EXCEL-IMPORT-001 -- POST /api/ltsa/condition-monitoring-
readings/import/parse and GET .../import/template: maintenance.write
authorization, non-.xlsx rejection, structural-failure-as-readable-422,
template column shape matches the canonical measurement catalog, and
that parsing performs ZERO database writes (no repository even wired
into these routes -- structurally impossible for them to write)."""

import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user, get_condition_monitoring_reading_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.condition_monitoring_excel_template import TEMPLATE_COLUMNS  # noqa: E402

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


# --- parse: zero DB writes ------------------------------------------------


class _RepositoryThatMustNeverBeCalled:
    """If the parse route ever touched a repository, calling any method
    on this fake raises -- proving Section 6/11's own "ZERO DB writes,
    ZERO readings created" requirement structurally, not by inference."""

    def __getattr__(self, name):
        raise AssertionError(f"parse route must never call repository.{name}() -- decode-only")


def test_parse_never_touches_the_reading_repository():
    _override("TAP_ENGINEER")
    app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: _RepositoryThatMustNeverBeCalled()
    data = _xlsx_bytes([("Pump Tag *", "Reading Date *"), ("211-P-1A", "2026-09-06")])

    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200  # would have raised via the fake above if it ever wrote anything


def test_parse_returns_the_raw_grid_unmodified():
    _override("TAP_ENGINEER")
    data = _xlsx_bytes([
        ("Pump Tag *", "Mechanical Seal Temp DE", "Mechanical Seal Temp NDE"),
        ("211-P-1A", "75.2", ""),
    ])

    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["headers"] == ["Pump Tag *", "Mechanical Seal Temp DE", "Mechanical Seal Temp NDE"]
    assert body["rows"] == [["211-P-1A", "75.2", None]]


# --- parse: authorization -------------------------------------------------


def test_pertamina_viewer_cannot_parse():
    _override("PERTAMINA_VIEWER")
    data = _xlsx_bytes([("Pump Tag *",), ("211-P-1A",)])

    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 403


def test_anonymous_parse_is_401():
    data = _xlsx_bytes([("Pump Tag *",), ("211-P-1A",)])
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 401


def test_non_xlsx_extension_is_rejected_before_parsing():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.csv", b"Pump Tag,Reading Date\n211-P-1A,2026-09-06", "text/csv")},
    )
    assert response.status_code == 422
    assert ".xlsx" in response.json()["detail"]


def test_xls_extension_is_also_rejected():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xls", b"not real xls bytes", "application/vnd.ms-excel")},
    )
    assert response.status_code == 422
    assert ".xlsx" in response.json()["detail"]


def test_structural_parse_failure_is_one_readable_422_never_a_crash():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/condition-monitoring-readings/import/parse",
        files={"file": ("readings.xlsx", b"not a real workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "object Object" not in response.text


# --- template ---------------------------------------------------------------


def test_tap_engineer_can_download_template():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/condition-monitoring-readings/import/template")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 0


def test_pertamina_viewer_cannot_download_template():
    _override("PERTAMINA_VIEWER")
    response = client.get("/api/ltsa/condition-monitoring-readings/import/template")
    assert response.status_code == 403


def test_anonymous_template_is_401():
    response = client.get("/api/ltsa/condition-monitoring-readings/import/template")
    assert response.status_code == 401


def test_template_columns_are_the_exact_canonical_pump_tag_and_reading_date_plus_measurement_set():
    assert TEMPLATE_COLUMNS[0] == "Pump Tag *"
    assert TEMPLATE_COLUMNS[1] == "Reading Date *"
    assert "Mechanical Seal Temp DE" in TEMPLATE_COLUMNS
    assert "Mechanical Seal Temp NDE" in TEMPLATE_COLUMNS
    assert "Mechanical Seal Leak DE" in TEMPLATE_COLUMNS
    assert "Mechanical Seal Leak NDE" in TEMPLATE_COLUMNS
    assert "Pump Operating State" in TEMPLATE_COLUMNS
    # No General column for any sided measurement -- the schema has none.
    assert not any(col.endswith(" General") for col in TEMPLATE_COLUMNS)
