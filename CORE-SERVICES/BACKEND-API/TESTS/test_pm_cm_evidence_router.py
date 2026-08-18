"""MWO-LTSA-PM-CM-INTAKE-001 -- PM/CM evidence upload/list/download route
tests: authorization, content-type/size rejection, uploader attribution."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app  # noqa: E402
from dependencies import get_current_user, get_pm_cm_evidence_repository  # noqa: E402
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity  # noqa: E402
from API.pm_cm_evidence_repository import FileTooLargeError, UnsupportedContentTypeError, validate_upload  # noqa: E402

client = TestClient(app)


def _identity(role: str, user_id: str = "actor-1") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id, email=f"{user_id}@tap.internal",
        organization_id="org-tap", organization_code="TAP",
        role=role, permissions=ROLE_PERMISSIONS[role],
    )


class FakeEvidenceRepository:
    def __init__(self):
        self.created: list[dict] = []

    def create(self, *, content_type, file_size_bytes=None, file_bytes=None, **kwargs):
        validate_upload(content_type=content_type, file_size_bytes=len(file_bytes))
        record = {"evidence_id": "evid-1", "content_type": content_type, **kwargs}
        self.created.append(record)
        return record

    def list_for_record(self, record_type, record_code):
        return [r for r in self.created if r.get("record_type") == record_type and r.get("record_code") == record_code]

    def get_file_data(self, evidence_id):
        return None


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _override(role: str, user_id: str = "actor-1"):
    fake = FakeEvidenceRepository()
    app.dependency_overrides[get_current_user] = lambda: _identity(role, user_id)
    app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: fake
    return fake


def test_tap_engineer_can_upload_a_photo():
    fake = _override("TAP_ENGINEER", user_id="real-actor")
    response = client.post(
        "/api/ltsa/pm-cm-evidence",
        data={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1", "category": "PHOTO"},
        files={"file": ("seal.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    )
    assert response.status_code == 200
    assert fake.created[0]["uploaded_by"] == "real-actor"
    assert fake.created[0]["source"] == "MANUAL"


def test_pertamina_engineer_cannot_upload_evidence():
    _override("PERTAMINA_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-cm-evidence",
        data={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1"},
        files={"file": ("seal.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    )
    assert response.status_code == 403


def test_unsupported_content_type_is_rejected_with_422():
    _override("TAP_ENGINEER")
    response = client.post(
        "/api/ltsa/pm-cm-evidence",
        data={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1"},
        files={"file": ("virus.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert response.status_code == 422


def test_anonymous_upload_is_401():
    app.dependency_overrides.clear()
    response = client.post(
        "/api/ltsa/pm-cm-evidence",
        data={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1"},
        files={"file": ("seal.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    )
    assert response.status_code == 401


def test_tap_engineer_can_list_evidence_for_a_record():
    _override("TAP_ENGINEER")
    client.post(
        "/api/ltsa/pm-cm-evidence",
        data={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1", "category": "PHOTO"},
        files={"file": ("seal.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    )
    response = client.get("/api/ltsa/pm-cm-evidence", params={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1"})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


def test_john_crane_engineer_can_list_evidence_read_only():
    _override("JOHN_CRANE_ENGINEER")
    response = client.get("/api/ltsa/pm-cm-evidence", params={"record_type": "PM_OCCURRENCE", "record_code": "PMOCC-1"})
    assert response.status_code == 200


def test_download_returns_404_for_an_unknown_evidence_id():
    _override("TAP_ENGINEER")
    response = client.get("/api/ltsa/pm-cm-evidence/evid-missing/download")
    assert response.status_code == 404
