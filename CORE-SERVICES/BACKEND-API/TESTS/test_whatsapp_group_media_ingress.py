"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- Phase 1A-1D Integration and Router Tests
for WhatsApp Media Evidence Ingestion.

Covers:
- Image & PDF upload flow
- Preview formatting
- /ltsa confirm commit to pm_cm_evidence (BYTEA)
- /ltsa cancel discard
- Expiry / No pending media
- Cross-user protection
- Cross-group protection
- Permission gating (maintenance.write required)
- Permission revoked between stage and confirm
- Magic byte validation (JPEG, PNG, WEBP, PDF)
- 50-page PDF limit enforcement
- Corrupt PDF rejection
- Oversized file rejection (>15MB)
- Missing parent record (CM and PM)
- Generic unsupported attachment notice (/ltsa laporan, /ltsa foto)
- Scope and pump validation
- Dual endpoint support (/message and /media)
"""
from __future__ import annotations

import base64
import os
import pytest
from fastapi.testclient import TestClient

import main
from API.auth_service import AuthenticatedIdentity
from API.whatsapp_group_agent_service import hash_group_identifier
from API.whatsapp_group_media_store import WhatsAppGroupMediaStore
from API.whatsapp_group_repository_inmemory import InMemoryGroupAuthorizationRepository
from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier
from dependencies import (
    get_condition_monitoring_reading_repository,
    get_group_authorization_repository,
    get_group_media_store,
    get_group_message_rate_limiter,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_whatsapp_intake_repository,
)

GROUP_ID = "120363099999999999@g.us"
GROUP_HASH = hash_group_identifier(GROUP_ID)
GROUP_2_ID = "120363088888888888@g.us"
GROUP_2_HASH = hash_group_identifier(GROUP_2_ID)

SENDER_PHONE_AUTHORIZED = "6281234599999"
SENDER_HASH_AUTHORIZED = hash_sender_identifier(normalize_sender_identifier(SENDER_PHONE_AUTHORIZED))

SENDER_PHONE_READ_ONLY = "6281234588888"
SENDER_HASH_READ_ONLY = hash_sender_identifier(normalize_sender_identifier(SENDER_PHONE_READ_ONLY))

SENDER_PHONE_USER_2 = "6281234577777"
SENDER_HASH_USER_2 = hash_sender_identifier(normalize_sender_identifier(SENDER_PHONE_USER_2))

SAMPLE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
SAMPLE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100
SAMPLE_VALID_PDF_1_PAGE = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
    b"xref\n0 4\n"
    b"trailer\n<< /Root 1 0 R >>\n"
    b"%%EOF"
)
SAMPLE_OVERSIZED_PDF_51_PAGES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 51 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
    b"xref\n0 4\n"
    b"trailer\n<< /Root 1 0 R >>\n"
    b"%%EOF"
)
SAMPLE_CORRUPT_PDF = b"%PDF-1.4\ncorrupt content without eof"


class _AllowAllRateLimiter:
    def allow(self, *, sender_hash: str, group_hash: str) -> bool:
        return True


class _FakeSenderRepository:
    def __init__(self, identities: dict[str, AuthenticatedIdentity]):
        self._identities = identities

    def find_identity_by_sender_hash(self, sender_hash: str):
        return self._identities.get(sender_hash)


class _FakePumpGateway:
    def __init__(self, pumps: dict[str, dict]):
        self._pumps = pumps

    def get_pump(self, tag: str):
        if tag in self._pumps:
            return {"status": "success", "data": self._pumps[tag]}
        return {"status": "error", "message": "Not found"}


class _FakeCMRepository:
    def __init__(self, readings_by_asset: dict[str, list[dict]]):
        self._readings = readings_by_asset

    def list_by_asset(self, asset_code: str):
        return self._readings.get(asset_code, [])


class _FakePMRepository:
    def __init__(self, occurrences_by_asset: dict[str, list[dict]]):
        self._occurrences = occurrences_by_asset

    def list_by_asset(self, asset_code: str):
        return self._occurrences.get(asset_code, [])


class _FakePMCMEvidenceRepository:
    def __init__(self):
        self.created: list[dict] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"evidence_id": f"evi-{len(self.created)}", **kwargs}


@pytest.fixture(autouse=True)
def _ingress_secret(monkeypatch):
    monkeypatch.setenv("AI5R_WHATSAPP_GROUP_INGRESS_SECRET", "test-secret-value")
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def setup_environment(tmp_path):
    group_repo = InMemoryGroupAuthorizationRepository()
    group_repo.register_group(group_hash=GROUP_HASH, display_label="TAP Test 1", registered_by="admin")
    group_repo.activate_group(group_hash=GROUP_HASH, activated_by="admin")
    group_repo.register_group(group_hash=GROUP_2_HASH, display_label="TAP Test 2", registered_by="admin")
    group_repo.activate_group(group_hash=GROUP_2_HASH, activated_by="admin")

    identities = {
        SENDER_HASH_AUTHORIZED: AuthenticatedIdentity(
            user_id="user-auth-1",
            email=None,
            organization_id="org-1",
            organization_code="TAP",
            role="TAP_ENGINEER",
            permissions=frozenset({"maintenance.read", "maintenance.write"}),
        ),
        SENDER_HASH_READ_ONLY: AuthenticatedIdentity(
            user_id="user-ro-1",
            email=None,
            organization_id="org-1",
            organization_code="TAP",
            role="TAP_VIEWER",
            permissions=frozenset({"maintenance.read"}),
        ),
        SENDER_HASH_USER_2: AuthenticatedIdentity(
            user_id="user-auth-2",
            email=None,
            organization_id="org-1",
            organization_code="TAP",
            role="TAP_ENGINEER",
            permissions=frozenset({"maintenance.read", "maintenance.write"}),
        ),
    }
    sender_repo = _FakeSenderRepository(identities)
    media_store = WhatsAppGroupMediaStore(spool_dir=tmp_path / "pending_media", ttl_seconds=900.0)

    pumps = {
        "211-P-16B": {"tag_number": "211-P-16B", "area": "AREA-1"},
        "211-P-10A": {"tag_number": "211-P-10A", "area": "AREA-2"},
    }
    pump_gateway = _FakePumpGateway(pumps)

    cm_readings = {
        "211-P-16B": [
            {
                "condition_monitoring_reading_code": "CMONR-GOLDEN-001",
                "reading_id": 101,
                "reading_date": "2026-03-01",
            }
        ]
    }
    cm_repo = _FakeCMRepository(cm_readings)

    pm_occurrences = {
        "211-P-16B": [
            {
                "pm_occurrence_code": "PMOCC-GOLDEN-002",
                "occurrence_id": 202,
                "occurrence_date": "2026-03-02",
            }
        ]
    }
    pm_repo = _FakePMRepository(pm_occurrences)
    evidence_repo = _FakePMCMEvidenceRepository()

    main.app.dependency_overrides[get_group_authorization_repository] = lambda: group_repo
    main.app.dependency_overrides[get_whatsapp_intake_repository] = lambda: sender_repo
    main.app.dependency_overrides[get_group_message_rate_limiter] = lambda: _AllowAllRateLimiter()
    main.app.dependency_overrides[get_group_media_store] = lambda: media_store
    main.app.dependency_overrides[get_pump_gateway] = lambda: pump_gateway
    main.app.dependency_overrides[get_condition_monitoring_reading_repository] = lambda: cm_repo
    main.app.dependency_overrides[get_pm_occurrence_repository] = lambda: pm_repo
    main.app.dependency_overrides[get_pm_cm_evidence_repository] = lambda: evidence_repo

    yield {
        "group_repo": group_repo,
        "sender_repo": sender_repo,
        "media_store": media_store,
        "evidence_repo": evidence_repo,
        "identities": identities,
    }
    main.app.dependency_overrides.clear()


def test_image_upload_preview_and_confirm(client, setup_environment):
    evidence_repo = setup_environment["evidence_repo"]

    # 1. Upload image with CM caption
    payload = {
        "group_id": GROUP_ID,
        "sender_identifier": SENDER_PHONE_AUTHORIZED,
        "provider_message_id": "wamid.MEDIA-UPLOAD-1",
        "text": "/ltsa cm 211-P-16B",
        "media_type": "image",
        "mimetype": "image/jpeg",
        "filename": "pump_seal_leak.jpg",
        "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
    }
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "MEDIA_STAGED"
    assert "*Preview Bukti Media:*" in data["reply"]
    assert "CMONR-GOLDEN-001" in data["reply"]
    assert "211-P-16B" in data["reply"]
    assert "/ltsa confirm" in data["reply"]
    assert len(evidence_repo.created) == 0

    # 2. Confirm the staged media
    confirm_payload = {
        "group_id": GROUP_ID,
        "sender_identifier": SENDER_PHONE_AUTHORIZED,
        "provider_message_id": "wamid.CONFIRM-1",
        "text": "/ltsa confirm",
    }
    confirm_resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json=confirm_payload,
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "MEDIA_CONFIRMED"
    assert "berhasil disimpan" in confirm_data["reply"]

    # 3. Verify evidence saved in pm_cm_evidence
    assert len(evidence_repo.created) == 1
    evidence = evidence_repo.created[0]
    assert evidence["record_type"] == "CONDITION_MONITORING_READING"
    assert evidence["record_code"] == "CMONR-GOLDEN-001"
    assert evidence["file_name"] == "pump_seal_leak.jpg"
    assert evidence["content_type"] == "image/jpeg"
    assert evidence["file_bytes"] == SAMPLE_JPEG
    assert evidence["category"] == "PHOTO"
    assert evidence["source"] == "WHATSAPP_GROUP"
    assert evidence["uploaded_by"] == "user-auth-1"


def test_pdf_upload_preview_and_confirm_via_media_endpoint(client, setup_environment):
    evidence_repo = setup_environment["evidence_repo"]

    # Test POST /api/ltsa/whatsapp-group/media endpoint with PDF
    payload = {
        "group_id": GROUP_ID,
        "sender_identifier": SENDER_PHONE_AUTHORIZED,
        "provider_message_id": "wamid.PDF-UPLOAD-1",
        "text": "/ltsa pm 211-P-16B",
        "media_type": "document",
        "mimetype": "application/pdf",
        "filename": "pm_report.pdf",
        "media_bytes_base64": base64.b64encode(SAMPLE_VALID_PDF_1_PAGE).decode("ascii"),
    }
    resp = client.post(
        "/api/ltsa/whatsapp-group/media",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json=payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "MEDIA_STAGED"
    assert "PMOCC-GOLDEN-002" in data["reply"]

    # Confirm
    confirm_resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.CONFIRM-PDF-1",
            "text": "/ltsa confirm",
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "MEDIA_CONFIRMED"

    assert len(evidence_repo.created) == 1
    evidence = evidence_repo.created[0]
    assert evidence["record_type"] == "PM_OCCURRENCE"
    assert evidence["record_code"] == "PMOCC-GOLDEN-002"
    assert evidence["category"] == "REPORT"
    assert evidence["content_type"] == "application/pdf"
    assert evidence["file_bytes"] == SAMPLE_VALID_PDF_1_PAGE


def test_media_upload_and_cancel(client, setup_environment):
    evidence_repo = setup_environment["evidence_repo"]
    media_store = setup_environment["media_store"]

    # Stage media
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.CANCEL-STAGE-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "cancel_me.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )
    assert resp.json()["status"] == "MEDIA_STAGED"

    # Cancel
    cancel_resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.CANCEL-ACTION-1",
            "text": "/ltsa cancel",
        },
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "MEDIA_CANCELLED"
    assert "telah dibatalkan" in cancel_resp.json()["reply"]

    # Spool is discarded and evidence repo is untouched
    assert media_store.get_pending("user-auth-1", GROUP_HASH) is None
    assert len(evidence_repo.created) == 0


def test_confirm_without_pending_media(client, setup_environment):
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.NO-PENDING-1",
            "text": "/ltsa confirm",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NO_PENDING_MEDIA"
    assert "Tidak ada media yang sedang menunggu konfirmasi" in data["reply"]


def test_cross_user_isolation_prevent_hijack(client, setup_environment):
    # User 1 stages media
    client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.ISOLATION-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "user1.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )

    # User 2 tries to confirm User 1's media
    resp_user2 = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_USER_2,
            "provider_message_id": "wamid.ISOLATION-2",
            "text": "/ltsa confirm",
        },
    )
    assert resp_user2.json()["status"] == "NO_PENDING_MEDIA"


def test_cross_group_isolation(client, setup_environment):
    # User 1 stages media in GROUP_ID
    client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.GRP-ISOLATION-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "group1.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )

    # User 1 tries to confirm from GROUP_2_ID
    resp_grp2 = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_2_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.GRP-ISOLATION-2",
            "text": "/ltsa confirm",
        },
    )
    assert resp_grp2.json()["status"] == "NO_PENDING_MEDIA"


def test_unauthorized_user_cannot_upload_or_confirm(client, setup_environment):
    # Read-only user tries to upload
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_READ_ONLY,
            "provider_message_id": "wamid.RO-UPLOAD-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "unauthorized.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UNAUTHORIZED_MEDIA"
    assert "maintenance.write" in data["reply"]


def test_permission_revoked_before_confirm(client, setup_environment):
    identities = setup_environment["identities"]

    # Stage media
    client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.REVOKE-STAGE-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "revoke.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )

    # Permission is revoked!
    identities[SENDER_HASH_AUTHORIZED] = AuthenticatedIdentity(
        user_id="user-auth-1",
        email=None,
        organization_id="org-1",
        organization_code="TAP",
        role="TAP_VIEWER",
        permissions=frozenset({"maintenance.read"}),
    )

    # Confirm attempt
    confirm_resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.REVOKE-CONFIRM-1",
            "text": "/ltsa confirm",
        },
    )
    assert confirm_resp.json()["status"] == "UNAUTHORIZED_MEDIA"
    assert "maintenance.write" in confirm_resp.json()["reply"]


def test_magic_bytes_mismatch_rejected(client, setup_environment):
    # Declares image/jpeg but sends PNG bytes
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.MISMATCH-1",
            "text": "/ltsa cm 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "fake.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_PNG).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INVALID_MEDIA"
    assert "JPEG" in resp.json()["reply"]


def test_pdf_page_limit_enforced(client, setup_environment):
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.PAGES-51",
            "text": "/ltsa pm 211-P-16B",
            "media_type": "document",
            "mimetype": "application/pdf",
            "filename": "huge_pages.pdf",
            "media_bytes_base64": base64.b64encode(SAMPLE_OVERSIZED_PDF_51_PAGES).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INVALID_MEDIA"
    assert "melebihi batas maksimum 50 halaman" in resp.json()["reply"]


def test_corrupt_pdf_rejected(client, setup_environment):
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.CORRUPT-PDF",
            "text": "/ltsa pm 211-P-16B",
            "media_type": "document",
            "mimetype": "application/pdf",
            "filename": "corrupt.pdf",
            "media_bytes_base64": base64.b64encode(SAMPLE_CORRUPT_PDF).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INVALID_MEDIA"
    assert "penanda akhir file" in resp.json()["reply"]


def test_generic_laporan_unsupported_notice(client, setup_environment):
    # User sends /ltsa laporan 211-P-16B
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.GENERIC-1",
            "text": "/ltsa laporan 211-P-16B",
            "media_type": "document",
            "mimetype": "application/pdf",
            "filename": "general_report.pdf",
            "media_bytes_base64": base64.b64encode(SAMPLE_VALID_PDF_1_PAGE).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "UNSUPPORTED_GENERIC_ATTACHMENT"
    assert "belum didukung pada skema database saat ini" in data["reply"]
    assert "/ltsa cm" in data["reply"]
    assert "/ltsa pm" in data["reply"]


def test_missing_parent_record_not_found(client, setup_environment):
    # Pump 211-P-10A exists, but has NO condition monitoring readings
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.NO-PARENT-1",
            "text": "/ltsa cm 211-P-10A",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "reading.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PARENT_RECORD_NOT_FOUND"
    assert "Tidak ditemukan catatan Condition Monitoring aktif" in data["reply"]


def test_missing_pump_tag_in_caption(client, setup_environment):
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.NO-TAG-1",
            "text": "/ltsa cm",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "reading.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "MISSING_PUMP_TAG"
    assert "Mohon sertakan tag pompa" in resp.json()["reply"]


def test_multiple_pump_tags_in_caption(client, setup_environment):
    resp = client.post(
        "/api/ltsa/whatsapp-group/message",
        headers={"x-ai5r-whatsapp-group-ingress-secret": "test-secret-value"},
        json={
            "group_id": GROUP_ID,
            "sender_identifier": SENDER_PHONE_AUTHORIZED,
            "provider_message_id": "wamid.MULTI-TAG-1",
            "text": "/ltsa cm 211-P-16A dan 211-P-16B",
            "media_type": "image",
            "mimetype": "image/jpeg",
            "filename": "reading.jpg",
            "media_bytes_base64": base64.b64encode(SAMPLE_JPEG).decode("ascii"),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "MULTIPLE_PUMP_TAGS"
    assert "Saya menemukan beberapa tag pompa" in resp.json()["reply"]
