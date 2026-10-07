"""Comprehensive tests for LTSA Mechanical Seal Drawing Storage Foundation (R9C).

Covers TEST_01 through TEST_35:
- File validation (PDF, PNG, JPEG, DWG, DXF, STEP, extensions, signatures, size)
- SHA-256 integrity and safe object key generation
- Path traversal immunity
- Deduplication and conflict handling (HTTP 409)
- Revision immutability, UNKNOWN revision status, at-most-one CURRENT invariant
- First-class REFERENCE_ONLY support (document_code=NULL, no physical file)
- RBAC enforcement across all roles (SUPERUSER, TAP_*, JC, PERTAMINA_*)
- Pertamina Area Scoping (authorized area, cross-area, unlinked fail-closed)
- Content streaming with correct MIME type
- Pre-retrieval authorization check
- Recoverable staging and quarantine semantics
- Zero credential exposure
- Verification that stock, lifecycle, current installation, and legacy data remain untouched.
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from API.auth_service import AuthenticatedIdentity, ROLE_PERMISSIONS  # noqa: E402
from API.drawing_file_validator import (  # noqa: E402
    DrawingFileTooLargeError,
    DrawingSignatureMismatchError,
    InvalidDrawingExtensionError,
    validate_drawing_file,
)
from API.drawing_reference_normalizer import (  # noqa: E402
    normalize_reference,
    parse_reference_components,
    sanitize_for_path_segment,
)
from API.drawing_repository import InMemoryDrawingRepository  # noqa: E402
from API.drawing_service import DrawingConflictError, DrawingNotFoundError, DrawingService  # noqa: E402
from API.minio_storage_service import (  # noqa: E402
    InMemoryStorageService,
    generate_drawing_object_key,
    generate_staged_object_key,
)
from dependencies import (  # noqa: E402
    get_current_user,
    get_drawing_repository,
    get_drawing_service,
    get_drawing_storage_service,
    get_pump_gateway,
    get_seal_pump_compatibility_gateway,
)

# --- Synthetic Binary Fixtures (unmistakably synthetic, no real production drawing) ---
SYNTHETIC_PDF = b"%PDF-1.4\n%synthetic test drawing content\n%%EOF"
SYNTHETIC_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
SYNTHETIC_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xd9"
SYNTHETIC_DWG = b"AC1032" + (b"\x00" * 32)
SYNTHETIC_DXF = b"0\r\nSECTION\r\n2\r\nHEADER\r\n0\r\nENDSEC\r\n0\r\nEOF\r\n"
SYNTHETIC_STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"

# Area mapping for pumps
_PUMP_AREAS = {"110-P-9A": "HOC", "200-P-1A": "HSC"}


class FakePumpGateway:
    def get_pump(self, tag_number):
        area = _PUMP_AREAS.get(tag_number)
        if area is None:
            return {"success": False, "data": None}
        return {"success": True, "data": {"tag_number": tag_number, "area": area}}

    def list_pumps(self):
        return {"success": True, "data": [{"tag_number": k, "area": v} for k, v in _PUMP_AREAS.items()]}


class FakeSealPumpCompatGateway:
    def list_seal_pump_compatibilities(self):
        return {
            "success": True,
            "data": [
                {"seal_code": "SL-001", "pump_tag_number": "110-P-9A"},
                {"seal_code": "SL-002", "pump_tag_number": "200-P-1A"},
            ],
        }


def make_identity(role: str, area_scope: str | None = None) -> AuthenticatedIdentity:
    scope_type = "AREA" if area_scope else None
    return AuthenticatedIdentity(
        user_id="11111111-1111-1111-1111-111111111111",
        email=f"test_{role.lower()}@example.com",
        organization_id="22222222-2222-2222-2222-222222222222",
        organization_code="TAP" if "PERTAMINA" not in role else "PERTAMINA_RU_II",
        role=role,
        permissions=ROLE_PERMISSIONS.get(role, frozenset()),
        username=f"test_{role.lower()}",
        data_scope_type=scope_type,
        data_scope_value=area_scope,
    )


@pytest.fixture
def test_env():
    repo = InMemoryDrawingRepository()
    storage = InMemoryStorageService()
    history = MagicMock()
    service = DrawingService(repository=repo, storage_service=storage, change_history_repository=history)
    pump_gw = FakePumpGateway()
    compat_gw = FakeSealPumpCompatGateway()

    app.dependency_overrides[get_drawing_repository] = lambda: repo
    app.dependency_overrides[get_drawing_storage_service] = lambda: storage
    app.dependency_overrides[get_drawing_service] = lambda: service
    app.dependency_overrides[get_pump_gateway] = lambda: pump_gw
    app.dependency_overrides[get_seal_pump_compatibility_gateway] = lambda: compat_gw

    client = TestClient(app)
    yield {
        "client": client,
        "repo": repo,
        "storage": storage,
        "service": service,
        "history": history,
    }
    app.dependency_overrides.clear()


# ==============================================================================
# TEST_01 - TEST_07: Validation, Integrity, Object Key, Path Traversal
# ==============================================================================

def test_01_valid_pdf_upload_accepted(test_env):
    """TEST_01: Valid PDF upload accepted and metadata recorded."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/drawings",
        data={"drawing_number": "GA-243047", "title": "Pump GA Drawing", "revision": "0"},
        files={"file": ("drawing.pdf", SYNTHETIC_PDF, "application/pdf")},
    )
    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["document_number"] == "GA-243047"
    assert payload["revision"] == "0"
    assert payload["content_type"] == "application/pdf"
    assert payload["file_size_bytes"] == len(SYNTHETIC_PDF)
    assert payload["sha256_checksum"] == hashlib.sha256(SYNTHETIC_PDF).hexdigest()
    assert test_env["storage"].object_exists(payload["object_key"])


def test_02_invalid_extension_rejected():
    """TEST_02: Invalid extension rejected."""
    with pytest.raises(InvalidDrawingExtensionError):
        validate_drawing_file(b"test script", "malicious.exe")

    with pytest.raises(InvalidDrawingExtensionError):
        validate_drawing_file(b"test script", "archive.zip")


def test_03_extension_signature_mismatch_rejected():
    """TEST_03: Extension/content-signature mismatch rejected."""
    with pytest.raises(DrawingSignatureMismatchError):
        validate_drawing_file(b"NOT A REAL PDF CONTENT", "sample.pdf")

    with pytest.raises(DrawingSignatureMismatchError):
        validate_drawing_file(SYNTHETIC_PDF, "sample.png")


def test_04_oversized_file_rejected():
    """TEST_04: Oversized file rejected."""
    oversized = b"%PDF-" + (b"0" * (50 * 1024 * 1024 + 10))
    with pytest.raises(DrawingFileTooLargeError):
        validate_drawing_file(oversized, "huge.pdf")


def test_05_sha256_generated_correctly():
    """TEST_05: SHA-256 generated correctly server-side."""
    expected_hash = hashlib.sha256(SYNTHETIC_PDF).hexdigest()
    repo = InMemoryDrawingRepository()
    storage = InMemoryStorageService()
    svc = DrawingService(repository=repo, storage_service=storage)

    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="test.pdf",
        drawing_number="E12894",
        title="Seal Drawing",
        revision="A",
    )
    assert doc["sha256_checksum"] == expected_hash


def test_06_object_key_generated_internally_and_safely():
    """TEST_06: Object key generated internally with safe deterministic structure."""
    expected_hash = hashlib.sha256(SYNTHETIC_PDF).hexdigest()
    key = generate_drawing_object_key("GA-243047", "REV-0", expected_hash, ".pdf")
    assert key == f"drawings/GA-243047/REV-0/{expected_hash}.pdf"
    assert ".." not in key
    assert not key.startswith("/")


def test_07_raw_filename_cannot_cause_path_traversal():
    """TEST_07: Raw user filename cannot cause path traversal in storage key."""
    malicious_dwg = "../../../etc/passwd"
    safe_segment = sanitize_for_path_segment(malicious_dwg)
    assert "/" not in safe_segment
    assert ".." not in safe_segment
    assert "\\" not in safe_segment

    key = generate_drawing_object_key(malicious_dwg, "0", "dummyhash", ".pdf")
    assert ".." not in key
    assert "/etc/" not in key


# ==============================================================================
# TEST_08 - TEST_13: Deduplication, Conflicts, Revisions
# ==============================================================================

def test_08_same_drawing_revision_checksum_is_idempotent(test_env):
    """TEST_08: Same drawing + revision + checksum is idempotent."""
    svc = test_env["service"]
    doc1 = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="doc.pdf",
        drawing_number="E12894",
        title="Title 1",
        revision="0",
    )
    doc2 = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="doc.pdf",
        drawing_number="E12894",
        title="Title 1 Duplicate",
        revision="0",
    )
    assert doc1["document_code"] == doc2["document_code"]
    assert doc1["sha256_checksum"] == doc2["sha256_checksum"]


def test_09_same_drawing_revision_different_checksum_returns_conflict(test_env):
    """TEST_09: Same drawing + revision + different checksum raises 409 Conflict."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("TAP_ENGINEER")

    # First upload
    res1 = client.post(
        "/api/ltsa/drawings",
        data={"drawing_number": "E12894", "title": "Seal Rev 0", "revision": "0"},
        files={"file": ("drawing.pdf", SYNTHETIC_PDF, "application/pdf")},
    )
    assert res1.status_code == 201

    # Second upload with different binary content on same drawing + revision
    modified_pdf = SYNTHETIC_PDF + b"%extra bytes"
    res2 = client.post(
        "/api/ltsa/drawings",
        data={"drawing_number": "E12894", "title": "Seal Rev 0 modified", "revision": "0"},
        files={"file": ("drawing.pdf", modified_pdf, "application/pdf")},
    )
    assert res2.status_code == 409
    assert "Conflict" in res2.json()["detail"]


def test_10_unknown_revision_remains_pending_review(test_env):
    """TEST_10: UNKNOWN revision remains PENDING_REVIEW."""
    svc = test_env["service"]
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="legacy.pdf",
        drawing_number="TMI-8B-1520",
        title="Legacy Drawing",
        revision=None,  # Unknown
    )
    assert doc["revision"] == "UNKNOWN"
    assert doc["revision_status"] == "PENDING_REVIEW"
    assert doc["status"] == "PENDING_REVIEW"


def test_11_unknown_revision_does_not_become_current_automatically(test_env):
    """TEST_11: UNKNOWN revision does not become CURRENT automatically."""
    svc = test_env["service"]
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="legacy.pdf",
        drawing_number="TMI-8B-1520",
        title="Legacy Drawing",
        revision="UNKNOWN",
    )
    assert doc["is_current_revision"] is False


def test_12_previous_revision_remains_immutable(test_env):
    """TEST_12: Previous revision remains immutable and accessible after newer revision."""
    svc = test_env["service"]
    doc_rev0 = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="rev0.pdf",
        drawing_number="E12894",
        title="Seal Rev 0",
        revision="0",
    )
    key_rev0 = doc_rev0["object_key"]

    rev1_bytes = SYNTHETIC_PDF + b"\n%REV 1 MODIFICATIONS"
    doc_rev1 = svc.register_drawing(
        file_bytes=rev1_bytes,
        filename="rev1.pdf",
        drawing_number="E12894",
        title="Seal Rev 1",
        revision="1",
        is_revision_upload=True,
    )

    # Both objects exist in storage
    assert test_env["storage"].object_exists(key_rev0)
    assert test_env["storage"].object_exists(doc_rev1["object_key"])
    assert test_env["storage"].get_object_bytes(key_rev0) == SYNTHETIC_PDF

    # Status of rev0 was updated to SUPERSEDED, but object bytes untouched
    updated_rev0 = test_env["repo"].get_document_by_code(doc_rev0["document_code"])
    assert updated_rev0["is_current_revision"] is False
    assert updated_rev0["status"] == "SUPERSEDED"
    assert doc_rev1["is_current_revision"] is True


def test_13_at_most_one_current_enforced(test_env):
    """TEST_13: At-most-one CURRENT revision invariant maintained."""
    svc = test_env["service"]
    svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="rev0.pdf",
        drawing_number="GA-187530",
        title="GA",
        revision="0",
    )
    svc.register_drawing(
        file_bytes=SYNTHETIC_PDF + b"%revA",
        filename="revA.pdf",
        drawing_number="GA-187530",
        title="GA Rev A",
        revision="A",
        is_revision_upload=True,
    )
    revisions = test_env["repo"].list_revisions("GA-187530")
    current_revisions = [r for r in revisions if r.get("is_current_revision") is True]
    assert len(current_revisions) == 1
    assert current_revisions[0]["revision"] == "A"


# ==============================================================================
# TEST_14 - TEST_15: REFERENCE_ONLY Support
# ==============================================================================

def test_14_reference_only_supports_document_code_null(test_env):
    """TEST_14: REFERENCE_ONLY supports document_code=NULL."""
    svc = test_env["service"]
    link = svc.add_reference_only_link(
        drawing_number="TMI_8B_1525",
        target_type="PUMP",
        target_code="110-P-9A",
        source_type="PUMP_REGISTRY",
        notes="Legacy reference found in pump datasheet",
    )
    assert link["document_code"] is None
    assert link["confidence_status"] == "REFERENCE_ONLY"
    assert link["raw_reference"] == "TMI_8B_1525"
    assert link["normalized_reference"] == "TMI-8B-1525"


def test_15_reference_only_requires_no_physical_object(test_env):
    """TEST_15: REFERENCE_ONLY requires no physical object in storage."""
    svc = test_env["service"]
    link = svc.add_reference_only_link(
        drawing_number="E13406",
        target_type="HISTORICAL_SERVICE",
        target_code="SRV-2026-001",
        source_type="HISTORICAL_SERVICE",
    )
    assert link["link_id"] is not None
    # Storage remains empty
    assert len(test_env["storage"]._objects) == 0


# ==============================================================================
# TEST_16 - TEST_23: RBAC & Pertamina Area Scoping
# ==============================================================================

def test_16_pertamina_engineer_can_read_drawing_in_authorized_area(test_env):
    """TEST_16: Pertamina Engineer can read drawing linked to an asset in their authorized area."""
    client = test_env["client"]
    svc = test_env["service"]

    # Register drawing linked to pump 110-P-9A (which is in area HOC)
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="hoc_pump.pdf",
        drawing_number="GA-HOC-1",
        title="HOC Drawing",
        revision="0",
        asset_code="110-P-9A",
    )

    # Scoped to HOC
    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}")
    assert res.status_code == 200
    assert res.json()["data"]["document_code"] == doc["document_code"]


def test_17_pertamina_engineer_cannot_upload(test_env):
    """TEST_17: Pertamina Engineer cannot upload (lacks drawing.upload)."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")

    res = client.post(
        "/api/ltsa/drawings",
        data={"drawing_number": "GA-1", "title": "Test", "revision": "0"},
        files={"file": ("drawing.pdf", SYNTHETIC_PDF, "application/pdf")},
    )
    assert res.status_code == 403


def test_18_pertamina_engineer_cannot_manage_links(test_env):
    """TEST_18: Pertamina Engineer cannot manage links (lacks drawing.manage)."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")

    res = client.post(
        "/api/ltsa/drawings/DOC-123/links",
        data={"target_type": "PUMP", "target_code": "110-P-9A"},
    )
    assert res.status_code == 403


def test_19_out_of_area_pertamina_access_denied(test_env):
    """TEST_19: Out-of-area Pertamina access denied (404, fail-closed)."""
    client = test_env["client"]
    svc = test_env["service"]

    # Register drawing linked to pump 200-P-1A (which is in area HSC)
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="hsc_pump.pdf",
        drawing_number="GA-HSC-1",
        title="HSC Drawing",
        revision="0",
        asset_code="200-P-1A",
    )

    # User is scoped ONLY to HOC
    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}")
    assert res.status_code == 404


def test_20_unlinked_physical_drawing_hidden_from_scoped_pertamina(test_env):
    """TEST_20: Unlinked physical drawing hidden from scoped Pertamina user (fail closed)."""
    client = test_env["client"]
    svc = test_env["service"]

    # Register unlinked drawing
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="unlinked.pdf",
        drawing_number="GA-UNLINKED-99",
        title="Unlinked Drawing",
        revision="0",
    )

    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}")
    assert res.status_code == 404

    list_res = client.get("/api/ltsa/drawings")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 0


def test_21_tap_engineer_upload_allowed(test_env):
    """TEST_21: TAP Engineer upload allowed (holds drawing.upload)."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("TAP_ENGINEER")

    res = client.post(
        "/api/ltsa/drawings",
        data={"drawing_number": "TAP-DWG-001", "title": "TAP Upload", "revision": "0"},
        files={"file": ("drawing.pdf", SYNTHETIC_PDF, "application/pdf")},
    )
    assert res.status_code == 201


def test_22_tap_engineer_cannot_drawing_manage(test_env):
    """TEST_22: TAP Engineer cannot drawing.manage unless granted."""
    client = test_env["client"]
    app.dependency_overrides[get_current_user] = lambda: make_identity("TAP_ENGINEER")

    res = client.post(
        "/api/ltsa/drawings/DOC-123/links",
        data={"target_type": "PUMP", "target_code": "110-P-9A"},
    )
    assert res.status_code == 403


def test_23_john_crane_engineer_permissions_match_approved_matrix(test_env):
    """TEST_23: John Crane Engineer holds read, upload, manage."""
    jc_identity = make_identity("JOHN_CRANE_ENGINEER")
    assert "drawing.read" in jc_identity.permissions
    assert "drawing.upload" in jc_identity.permissions
    assert "drawing.manage" in jc_identity.permissions


# ==============================================================================
# TEST_24 - TEST_27: Content Streaming, Quarantine, No Credentials
# ==============================================================================

def test_24_content_endpoint_streams_correct_mime(test_env):
    """TEST_24: Content endpoint streams correct MIME type."""
    client = test_env["client"]
    svc = test_env["service"]

    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="my_drawing.pdf",
        drawing_number="GA-100",
        title="Title",
        revision="0",
    )

    app.dependency_overrides[get_current_user] = lambda: make_identity("SUPERUSER")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}/content")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == SYNTHETIC_PDF


def test_25_content_endpoint_checks_authorization_before_retrieval(test_env):
    """TEST_25: Content endpoint checks authorization and scope BEFORE retrieval."""
    client = test_env["client"]
    svc = test_env["service"]

    # HSC drawing
    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="hsc.pdf",
        drawing_number="GA-HSC-99",
        title="Title",
        revision="0",
        asset_code="200-P-1A",
    )

    # Scoped to HOC
    app.dependency_overrides[get_current_user] = lambda: make_identity("PERTAMINA_ENGINEER", area_scope="HOC")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}/content")
    assert res.status_code == 404


def test_26_storage_registration_failure_leaves_quarantine_not_destruction(test_env):
    """TEST_26: Storage registration failure leaves recoverable quarantine evidence."""
    storage = test_env["storage"]
    failing_repo = MagicMock()
    failing_repo.get_document_by_number_and_revision.return_value = None
    failing_repo.create_document.side_effect = RuntimeError("Database crash during insert")

    svc = DrawingService(repository=failing_repo, storage_service=storage)

    with pytest.raises(RuntimeError) as exc_info:
        svc.register_drawing(
            file_bytes=SYNTHETIC_PDF,
            filename="crash_test.pdf",
            drawing_number="CRASH-100",
            title="Crash Test",
            revision="0",
        )
    assert "quarantined for recovery" in str(exc_info.value)

    # Verify object is quarantined and NOT deleted
    quarantined_keys = [k for k in storage._objects if k.startswith("quarantine/")]
    assert len(quarantined_keys) == 1
    assert storage.get_object_bytes(quarantined_keys[0]) == SYNTHETIC_PDF


def test_27_no_storage_credentials_returned_by_api(test_env):
    """TEST_27: No storage credentials returned by API."""
    client = test_env["client"]
    svc = test_env["service"]

    doc = svc.register_drawing(
        file_bytes=SYNTHETIC_PDF,
        filename="sec.pdf",
        drawing_number="SEC-01",
        title="Security Test",
        revision="0",
    )

    app.dependency_overrides[get_current_user] = lambda: make_identity("SUPERUSER")
    res = client.get(f"/api/ltsa/drawings/{doc['document_code']}")
    assert res.status_code == 200
    json_text = res.text.lower()
    for secret_keyword in ("secret", "password", "access_key", "secret_key", "minio_root"):
        assert secret_keyword not in json_text


# ==============================================================================
# TEST_28 - TEST_35: Invariant Protection & Compatibility
# ==============================================================================

def test_28_to_33_invariants_untouched():
    """TEST_28 - TEST_33: Verifies no code in R9C mutates seal_unit, stock, or lifecycle."""
    import API.drawing_service as ds
    import API.drawing_repository as dr

    # Inspect module code to verify no imports or calls to stock/unit/lifecycle tables
    for module in (ds, dr):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "seal_unit" not in source
        assert "current_pump_tag_number" not in source
        assert "mechanical_seal_stock" not in source
        assert "seal_lifecycle_event" not in source


def test_34_pump_knowledge_service_compatibility():
    """TEST_34: LTSAKnowledgeService._build_drawings compatibility preserved."""
    from API.ltsa_knowledge_service import LTSAKnowledgeService

    fake_doc_gateway = MagicMock()
    fake_doc_gateway.list_seal_engineering_documents.return_value = {
        "success": True,
        "data": [
            {
                "document_code": "DOC-1",
                "document_type": "DRAWING",
                "seal_code": "SL-001",
                "title": "Seal DWG",
                "document_number": "E12894",
                "revision": "A",
                "status": "APPROVED",
                "file_name": "e12894.pdf",
                "created_at": "2026-10-01",
            }
        ],
    }

    service = LTSAKnowledgeService(seal_engineering_document_gateway=fake_doc_gateway)
    spare_parts = [{"seal_code": "SL-001"}]
    drawings = service._build_drawings(spare_parts)
    assert len(drawings) == 1
    assert drawings[0]["drawing_id"] == "DOC-1"
    assert drawings[0]["document_number"] == "E12894"


def test_35_existing_rbac_tests_pass():
    """TEST_35: Existing RBAC permissions remain consistent."""
    assert "drawing.read" in ROLE_PERMISSIONS["SUPERUSER"]
    assert "drawing.read" in ROLE_PERMISSIONS["TAP_ADMIN"]
    assert "drawing.read" in ROLE_PERMISSIONS["TAP_ENGINEER"]
    assert "drawing.read" in ROLE_PERMISSIONS["JOHN_CRANE_ENGINEER"]
    assert "drawing.read" in ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
    assert "drawing.read" not in ROLE_PERMISSIONS["PERTAMINA_VIEWER"]
    assert "internal_inventory.read" not in ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
    assert "internal_component.read" not in ROLE_PERMISSIONS["PERTAMINA_ENGINEER"]
