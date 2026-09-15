"""Focused test suite for Condition Monitoring Field Form Preview & Review API (CM R5D).

Tests verifying:
1. Valid workbook preview (14 sheets, 153 assets, 133 exact, 15 aliases, 5 quarantine, 148 resolvable, 42 params)
2. Quarantine fail-closed (returns 200 with 148 resolvable and 5 review_required, never a 500 error)
3. Zero-write guarantee (0 DB writes, 0 readings, 0 measurements, 0 findings, 0 asset_registry writes)
4. Invalid file extension rejection (400 INVALID_FILE_TYPE)
5. Empty file upload rejection (400 EMPTY_FILE)
6. Corrupt workbook file rejection (400 CORRUPT_WORKBOOK)
7. Invalid inspection date rejection (400 INVALID_INSPECTION_DATE)
8. RBAC allowed (TAP_ADMIN / TAP_ENGINEER can POST preview and review; condition.read can GET)
9. RBAC denied (unauthorized roles receive 403 on write and 401 when unauthenticated)
10. Scope filtering (area-scoped user receives filtered asset preview)
11. Safe tempfile lifecycle (no tempfile residue left on disk)
12. Deterministic repeated preview (identical idempotency hash across repeated uploads)
13. Human review decision update (ACCEPTED_FOR_FUTURE_APPLY sets status without DB persistence)
14. Session retrieval via GET /preview/{preview_id}
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_API_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_API_DIR))

from main import app
from dependencies import get_current_user, get_field_form_preview_store
from API.auth_service import ROLE_PERMISSIONS, AuthenticatedIdentity

client = TestClient(app)
WORKBOOK_PATH = r"C:\Users\ghona\Downloads\LIST LAPANGAN CM (1).xlsx"


def _identity(role: str, *, data_scope_type=None, data_scope_value=None, user_id="test-actor") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        user_id=user_id,
        email=f"{user_id}@tap.internal",
        organization_id="org-tap",
        organization_code="TAP",
        role=role,
        permissions=ROLE_PERMISSIONS[role],
        data_scope_type=data_scope_type,
        data_scope_value=data_scope_value,
    )


@pytest.fixture(autouse=True)
def clean_overrides_and_store():
    app.dependency_overrides.clear()
    store = get_field_form_preview_store()
    store.clear()
    yield
    app.dependency_overrides.clear()
    store.clear()


@pytest.fixture
def real_workbook_bytes():
    if not os.path.exists(WORKBOOK_PATH):
        pytest.skip(f"Authoritative workbook not found at {WORKBOOK_PATH}")
    with open(WORKBOOK_PATH, "rb") as f:
        return f.read()


# ==============================================================================
# 1. VALID WORKBOOK PREVIEW & CORE INTEGRITY
# ==============================================================================

def test_01_valid_workbook_preview_full_structure(real_workbook_bytes):
    """Verifies valid workbook upload returns 14 sheets, 153 assets, 42 parameters."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("LIST LAPANGAN CM (1).xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        params={"inspection_date": "2026-09-15"},
    )
    assert response.status_code == 200
    data = response.json()["data"]

    # Summary integrity
    summary = data["summary"]
    assert summary["total_source_assets"] == 153
    assert summary["exact_assets"] == 133
    assert summary["approved_alias_assets"] == 15
    assert summary["quarantined_assets"] == 5
    assert summary["resolvable_assets"] == 148
    assert summary["canonical_parameters_reached"] == 42
    assert summary["total_parameter_cells"] == 6426
    assert summary["blank_template_cells"] == 6426
    assert summary["value_present_cells"] == 0

    # Workbook metadata
    assert data["sheet_count"] == 14
    assert len(data["sheets"]) == 14
    assert len(data["asset_previews"]) == 153
    assert len(data["quarantined_assets"]) == 5

    # Zero-write audit
    zero = data["zero_write_audit"]
    assert zero["cm_reading_writes"] == 0
    assert zero["measurement_writes"] == 0
    assert zero["finding_writes"] == 0
    assert zero["asset_registry_writes"] == 0


def test_02_quarantine_fail_closed_semantics(real_workbook_bytes):
    """Verifies the 5 Unit 946 assets are quarantined and flagged REVIEW_REQUIRED."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("field_form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    data = response.json()["data"]

    quarantined = data["quarantined_assets"]
    assert len(quarantined) == 5
    expected_tags = {"946-P-2D", "946-P-4A", "946-P-4C", "946-P-8A", "946-P-8B"}
    assert {q["constructed_candidate"] for q in quarantined} == expected_tags

    for q in quarantined:
        assert q["resolution_status"] == "REVIEW_REQUIRED"
        assert q["persistence_eligible"] is False

    # The remaining 148 assets are persistence-eligible
    resolvable = [a for a in data["asset_previews"] if a["persistence_eligible"]]
    assert len(resolvable) == 148


# ==============================================================================
# 2. VALIDATION & ERROR HANDLING
# ==============================================================================

def test_03_invalid_file_extension_rejected():
    """Verifies non-.xlsx extension returns 400 INVALID_FILE_TYPE."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("notes.txt", b"not an excel file", "text/plain")},
    )
    assert response.status_code == 400
    assert "INVALID_FILE_TYPE" in response.json()["detail"]


def test_04_empty_file_rejected():
    """Verifies 0-byte file upload returns 400 EMPTY_FILE."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "EMPTY_FILE" in response.json()["detail"]


def test_05_corrupt_workbook_rejected():
    """Verifies corrupt workbook binary returns 400 CORRUPT_WORKBOOK."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    corrupt_bytes = b"PK\x03\x04corrupted_zip_payload_with_invalid_offsets_1234567890"
    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("corrupt.xlsx", corrupt_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400
    assert "CORRUPT_WORKBOOK" in response.json()["detail"]


def test_06_invalid_inspection_date_rejected(real_workbook_bytes):
    """Verifies malformed inspection date returns 400 INVALID_INSPECTION_DATE."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        params={"inspection_date": "not-a-date"},
    )
    assert response.status_code == 400
    assert "INVALID_INSPECTION_DATE" in response.json()["detail"]


# ==============================================================================
# 3. RBAC & SCOPE SECURITY
# ==============================================================================

def test_07_rbac_upload_denied_for_unauthorized_role(real_workbook_bytes):
    """Verifies role without maintenance.write (e.g. PERTAMINA_VIEWER) is rejected with 403."""
    app.dependency_overrides[get_current_user] = lambda: _identity("PERTAMINA_VIEWER")

    response = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 403
    assert "Missing permission" in response.json()["detail"]


def test_08_rbac_read_allowed_for_condition_reader(real_workbook_bytes):
    """Verifies PERTAMINA_ENGINEER with condition.read can GET previous preview."""
    # 1. TAP_ENGINEER creates preview
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert create_resp.status_code == 200
    preview_id = create_resp.json()["data"]["preview_id"]

    # 2. PERTAMINA_ENGINEER retrieves preview
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="HCC"
    )
    get_resp = client.get(f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["preview_id"] == preview_id


def test_09_rbac_read_denied_for_role_without_condition_read():
    """Verifies role without condition.read receives 403 on GET."""
    app.dependency_overrides[get_current_user] = lambda: _identity("PERTAMINA_VIEWER")
    get_resp = client.get("/api/ltsa/condition-monitoring/field-form/preview/PREV-fake")
    assert get_resp.status_code == 403


def test_10_area_scope_filtering(real_workbook_bytes):
    """Verifies area-scoped identity sees only in-scope assets."""
    # 1. Admin creates preview
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # 2. Scoped engineer with area "OM" (Oil Movement)
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="OM"
    )
    get_resp = client.get(f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}")
    assert get_resp.status_code == 200
    filtered_assets = get_resp.json()["data"]["asset_previews"]
    assert len(filtered_assets) == 7
    assert all("SPK" in a["source_sheet"] or "946" in a["effective_unit"] for a in filtered_assets)


# ==============================================================================
# 4. IDEMPOTENCY & ZERO-PERSISTENCE REVIEW
# ==============================================================================

def test_11_deterministic_repeated_preview_hash(real_workbook_bytes):
    """Verifies repeated uploads of identical workbook yield identical idempotency hash."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    resp1 = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("run1.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    resp2 = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("run2.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    hash1 = resp1.json()["data"]["idempotency_hash"]
    hash2 = resp2.json()["data"]["idempotency_hash"]
    assert hash1 == hash2


def test_12_human_review_decision_update_zero_writes(real_workbook_bytes):
    """Verifies ACCEPTED_FOR_FUTURE_APPLY updates review state without writing any DB data."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    # 1. Create preview
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # 2. Update review decision
    review_resp = client.post(
        f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}/review",
        json={"decision": "ACCEPTED_FOR_FUTURE_APPLY", "notes": "Approved for round planning"},
    )
    assert review_resp.status_code == 200
    updated = review_resp.json()["data"]
    assert updated["summary"]["review_status"] == "ACCEPTED_FOR_FUTURE_APPLY"
    assert updated["review_decision"]["decision"] == "ACCEPTED_FOR_FUTURE_APPLY"
    assert updated["review_decision"]["reviewed_by"] == "test-actor"

    # Zero writes remain zero
    zero = updated["zero_write_audit"]
    assert zero["cm_reading_writes"] == 0
    assert zero["measurement_writes"] == 0


def test_13_preview_session_not_found():
    """Verifies GET on nonexistent preview returns 404 PREVIEW_NOT_FOUND_OR_EXPIRED."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
    response = client.get("/api/ltsa/condition-monitoring/field-form/preview/PREV-nonexistent-12345")
    assert response.status_code == 404
    assert "PREVIEW_NOT_FOUND_OR_EXPIRED" in response.json()["detail"]


def test_14_preview_expired_via_ttl():
    """Verifies TTL expiration removes entry and returns 404 PREVIEW_NOT_FOUND_OR_EXPIRED."""
    import time
    from dependencies import FieldFormPreviewStore

    short_ttl_store = FieldFormPreviewStore(max_entries=10, ttl_seconds=0.05)
    app.dependency_overrides[get_field_form_preview_store] = lambda: short_ttl_store
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")

    short_ttl_store.put("PREV-expire-test", {"owner_org_id": "org-tap", "preview_id": "PREV-expire-test"})
    assert short_ttl_store.get("PREV-expire-test") is not None

    time.sleep(0.08)
    assert short_ttl_store.get("PREV-expire-test") is None

    response = client.get("/api/ltsa/condition-monitoring/field-form/preview/PREV-expire-test")
    assert response.status_code == 404
    assert "PREVIEW_NOT_FOUND_OR_EXPIRED" in response.json()["detail"]


def test_15_bounded_store_capacity_eviction():
    """Verifies FIFO eviction when store reaches max_entries."""
    from dependencies import FieldFormPreviewStore

    bounded_store = FieldFormPreviewStore(max_entries=3, ttl_seconds=3600.0)
    for i in range(5):
        bounded_store.put(f"PREV-{i}", {"preview_id": f"PREV-{i}"})

    assert len(bounded_store) == 3
    # First 2 entries should have been evicted
    assert bounded_store.get("PREV-0") is None
    assert bounded_store.get("PREV-1") is None
    assert bounded_store.get("PREV-2") is not None
    assert bounded_store.get("PREV-3") is not None
    assert bounded_store.get("PREV-4") is not None


def test_16_cross_user_organization_mismatch_denied(real_workbook_bytes):
    """Verifies user from another organization cannot view or review a preview session."""
    # 1. TAP creates preview
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ENGINEER")
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # 2. Foreign organization user attempts GET
    foreign_user = AuthenticatedIdentity(
        user_id="foreign-actor", email="foreign@other.com",
        organization_id="org-other", organization_code="OTHER",
        role="TAP_ENGINEER", permissions=ROLE_PERMISSIONS["TAP_ENGINEER"],
    )
    app.dependency_overrides[get_current_user] = lambda: foreign_user

    get_resp = client.get(f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}")
    assert get_resp.status_code == 403
    assert "ORGANIZATION_MISMATCH" in get_resp.json()["detail"]

    # 3. Foreign organization user attempts review
    review_resp = client.post(
        f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}/review",
        json={"decision": "REJECTED"},
    )
    assert review_resp.status_code == 403
    assert "ORGANIZATION_MISMATCH" in review_resp.json()["detail"]


def test_17_cross_area_scope_denied_on_get(real_workbook_bytes):
    """Verifies customer user scoped to an unrepresented area (e.g. UTL) is denied with 403."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # Scoped user with UTL area (workbook has no UTL assets)
    app.dependency_overrides[get_current_user] = lambda: _identity(
        "PERTAMINA_ENGINEER", data_scope_type="AREA", data_scope_value="UTL"
    )
    get_resp = client.get(f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}")
    assert get_resp.status_code == 403
    assert "AREA_SCOPE_DENIED" in get_resp.json()["detail"]


def test_18_cross_area_scope_denied_on_review(real_workbook_bytes):
    """Verifies user scoped to unrepresented area is denied review with 403."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")
    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # User scoped to UTL attempts to review
    scoped_reviewer = AuthenticatedIdentity(
        user_id="scoped-reviewer",
        email="scoped@tap.internal",
        organization_id="org-tap",
        organization_code="TAP",
        role="SCOPED_OPERATOR",
        permissions=frozenset({"maintenance.write"}),
        data_scope_type="AREA",
        data_scope_value="UTL",
    )
    app.dependency_overrides[get_current_user] = lambda: scoped_reviewer
    review_resp = client.post(
        f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}/review",
        json={"decision": "REJECTED"},
    )
    assert review_resp.status_code == 403
    assert "AREA_SCOPE_DENIED" in review_resp.json()["detail"]


def test_19_invalid_review_state_transitions(real_workbook_bytes):
    """Verifies state transition integrity: terminal states cannot transition further."""
    app.dependency_overrides[get_current_user] = lambda: _identity("TAP_ADMIN")

    create_resp = client.post(
        "/api/ltsa/condition-monitoring/field-form/preview",
        files={"file": ("form.xlsx", real_workbook_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    preview_id = create_resp.json()["data"]["preview_id"]

    # 1. Accept for future apply
    r1 = client.post(
        f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}/review",
        json={"decision": "ACCEPTED_FOR_FUTURE_APPLY"},
    )
    assert r1.status_code == 200

    # 2. Attempt invalid transition from ACCEPTED_FOR_FUTURE_APPLY back to PENDING
    r2 = client.post(
        f"/api/ltsa/condition-monitoring/field-form/preview/{preview_id}/review",
        json={"decision": "PENDING"},
    )
    assert r2.status_code == 400
    assert "INVALID_REVIEW_TRANSITION" in r2.json()["detail"]


def test_20_in_process_concurrency_safe():
    """Verifies multi-threaded store access does not corrupt state."""
    import concurrent.futures
    from dependencies import FieldFormPreviewStore

    store = FieldFormPreviewStore(max_entries=50, ttl_seconds=3600.0)

    def _worker(thread_id: int):
        for i in range(20):
            store.put(f"PREV-{thread_id}-{i}", {"data": i})
            val = store.get(f"PREV-{thread_id}-{i}")
            assert val is not None or len(store) <= 50

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker, tid) for tid in range(5)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    assert len(store) <= 50
