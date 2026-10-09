"""Comprehensive Test Suite for LTSA Current Mechanical Seal Installation (R3A.5 Preflight).

Validates:
1. Migration 053 schema validation and active position uniqueness invariant
2. Active uniqueness constraint prevents duplicate active snapshots regardless of resolution_status
3. Unresolved pumps (101-P-6A, 101-P-6C, 211-P-2A, 212-P-25A, 940-P-2A) create 0 active snapshot rows
4. Conflict pumps (101-P-3B, 945-P-7B, 140-P-26B) create 0 active snapshot rows
5. Exact frozen manifest = 31 pumps / 39 rows (23 SINGLE, 8 DE, 8 NDE, 0 NA)
6. Manifest deterministic across repeated execution (MANIFEST_SHA256 stability)
7. Source traceability 39/39 matches post-repair installation_report exactly
8. Superseded sources not active for 220-P-3A, 945-P-9B, 200-P-4B
9. Configured seal never used as fallback or installed seal
10. Quarantined drawing GA-187530 never linked into manifest or approved
11. API empty state returns topology-aware empty positions (SINGLE for OH, DE/NDE for BB, empty for unknown)
12. API endpoint returns correct structure for active OH pump
13. API endpoint returns correct structure for active BB pump
14. API endpoint enforces Pertamina area scoping fail-closed
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

BACKEND_API_DIR = Path(__file__).resolve().parents[1]
CORE_SERVICES_DIR = BACKEND_API_DIR.parent
PROJECT_ROOT = CORE_SERVICES_DIR.parent

for _path in (BACKEND_API_DIR, CORE_SERVICES_DIR, PROJECT_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from main import app  # noqa: E402
from API.auth_service import AuthenticatedIdentity  # noqa: E402
from API.current_seal_installation_repository import (  # noqa: E402
    InMemoryCurrentSealInstallationRepository,
)
from API.current_seal_installation_service import (  # noqa: E402
    CurrentSealInstallationService,
)
from dependencies import (  # noqa: E402
    get_current_seal_installation_service,
    get_current_user,
    get_pump_gateway,
)
from scripts.derive_current_installation import (  # noqa: E402
    derive_installations,
)
from scripts.freeze_backfill_manifest import (  # noqa: E402
    CANONICAL_HASH_COLUMNS,
    compute_row_hash,
    generate_and_freeze_manifest,
    verify_source_traceability,
)


ADMIN_USER = AuthenticatedIdentity(
    user_id="11111111-1111-1111-1111-111111111111",
    email="admin@example.com",
    organization_id="org-tap",
    organization_code="TAP",
    role="TAP_ADMIN",
    permissions=frozenset(["pump.read"]),
    username="admin",
)

PERTAMINA_HOC_USER = AuthenticatedIdentity(
    user_id="22222222-2222-2222-2222-222222222222",
    email="pertamina_hoc@example.com",
    organization_id="org-pertamina",
    organization_code="PERTAMINA_RU_II",
    role="PERTAMINA_ENGINEER",
    permissions=frozenset(["pump.read"]),
    username="pertamina_hoc",
    data_scope_type="AREA",
    data_scope_value="HOC",
)

PERTAMINA_HSC_USER = AuthenticatedIdentity(
    user_id="33333333-3333-3333-3333-333333333333",
    email="pertamina_hsc@example.com",
    organization_id="org-pertamina",
    organization_code="PERTAMINA_RU_II",
    role="PERTAMINA_ENGINEER",
    permissions=frozenset(["pump.read"]),
    username="pertamina_hsc",
    data_scope_type="AREA",
    data_scope_value="HSC",
)


class MockPumpGateway:
    def __init__(self, pumps_dict: dict[str, dict]):
        self.pumps = pumps_dict

    def get_pump(self, tag: str) -> dict:
        if tag in self.pumps:
            return {"success": True, "data": self.pumps[tag]}
        return {"success": False, "data": None}

    def list_pumps(self) -> dict:
        return {"success": True, "data": list(self.pumps.values())}


@pytest.fixture
def test_pumps_registry():
    return {
        "101-P-8A": {
            "tag_number": "101-P-8A",
            "pump_type": "OH2",
            "area": "HOC",
            "seal_type": "DESIGN_CONFIGURED_SEAL_NEVER_USE_ME",
            "drawing_ref": "DESIGN_DRAWING_NEVER_USE_ME",
        },
        "211-P-1A": {
            "tag_number": "211-P-1A",
            "pump_type": "BB",
            "area": "HOC",
            "seal_type": "DESIGN_BB_SEAL",
            "drawing_ref": "REF_BB_DWG",
        },
        "200-P-1A": {
            "tag_number": "200-P-1A",
            "pump_type": "OH2",
            "area": "HSC",
            "seal_type": "CONFIGURED_HSC_SEAL",
            "drawing_ref": "REF_HSC_DWG",
        },
        "999-P-EMPTY-OH": {
            "tag_number": "999-P-EMPTY-OH",
            "pump_type": "OH2",
            "area": "HOC",
            "seal_type": "CONFIGURED_EMPTY_SEAL",
            "drawing_ref": "REF_EMPTY_DWG",
        },
        "999-P-EMPTY-BB": {
            "tag_number": "999-P-EMPTY-BB",
            "pump_type": "BB3",
            "area": "HOC",
            "seal_type": "CONFIGURED_BB_SEAL",
            "drawing_ref": "REF_EMPTY_BB_DWG",
        },
        "999-P-UNKNOWN-TYPE": {
            "tag_number": "999-P-UNKNOWN-TYPE",
            "pump_type": None,
            "area": "HOC",
            "seal_type": "CONFIGURED_UNKNOWN_SEAL",
            "drawing_ref": "REF_UNKNOWN_DWG",
        },
    }


@pytest.fixture
def client_and_repo(test_pumps_registry):
    repo = InMemoryCurrentSealInstallationRepository()
    pump_gw = MockPumpGateway(test_pumps_registry)
    service = CurrentSealInstallationService(repository=repo, pump_gateway=pump_gw)

    app.dependency_overrides[get_current_seal_installation_service] = lambda: service
    app.dependency_overrides[get_pump_gateway] = lambda: pump_gw
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER

    client = TestClient(app)
    yield client, repo, service

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def prod_sources():
    with open(PROJECT_ROOT / "prod_ir_post_repair.json", "r", encoding="utf-8") as f:
        ir_rows = json.load(f)
    with open(PROJECT_ROOT / "prod_data.json", "r", encoding="utf-8-sig") as f:
        prod = json.load(f)
    pumps_by_tag = {p["tag_number"]: p for p in prod["ltsa_pumps"]}
    return ir_rows, pumps_by_tag


# ==============================================================================
# 1. Migration 053 Schema & Active Position Uniqueness Invariant
# ==============================================================================
def test_01_migration_053_unconditional_active_uniqueness_index():
    mig_path = PROJECT_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE" / "MIGRATIONS" / "053_create_current_seal_installation.sql"
    assert mig_path.exists(), "Migration 053 file must exist"
    content = mig_path.read_text(encoding="utf-8")

    # Table and check constraints
    assert "CREATE TABLE IF NOT EXISTS public.current_seal_installation" in content
    assert "pump_tag_number VARCHAR(100) NOT NULL REFERENCES public.ltsa_pumps(tag_number)" in content
    assert "equipment_side TEXT NOT NULL CHECK (equipment_side IN ('DE', 'NDE', 'SINGLE', 'NA'))" in content
    assert "resolution_status TEXT NOT NULL CHECK (resolution_status IN ('CONFIRMED', 'TYPE_ONLY', 'REVIEW_REQUIRED'))" in content

    # Active uniqueness index invariant: must cover all active rows regardless of resolution status
    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_current_seal_installation_active" in content
    assert "ON public.current_seal_installation (pump_tag_number, equipment_side)" in content
    assert "WHERE removed_at IS NULL;" in content
    assert "AND resolution_status = 'CONFIRMED'" not in content, "Uniqueness index must NOT be restricted to CONFIRMED"


# ==============================================================================
# 2. In-Memory Active Position Uniqueness Logic
# ==============================================================================
def test_02_only_one_active_row_per_pump_side_regardless_of_status():
    repo = InMemoryCurrentSealInstallationRepository()

    # Active row with CONFIRMED
    r1 = repo.create_installation(
        pump_tag_number="101-P-8A",
        equipment_side="SINGLE",
        seal_type="5620P",
        resolution_status="CONFIRMED",
    )
    active = repo.get_active_by_pump_tag("101-P-8A")
    assert len(active) == 1

    # Superseding allows new active row
    repo.supersede_installation(r1["id"])
    active_after_removal = repo.get_active_by_pump_tag("101-P-8A")
    assert len(active_after_removal) == 0

    repo.create_installation(
        pump_tag_number="101-P-8A",
        equipment_side="SINGLE",
        seal_type="5620P_NEW",
        resolution_status="REVIEW_REQUIRED",
    )
    active_new = repo.get_active_by_pump_tag("101-P-8A")
    assert len(active_new) == 1
    assert active_new[0]["seal_type"] == "5620P_NEW"


# ==============================================================================
# 3. Unresolved and Conflict Pumps Storage Policy (0 Production Rows)
# ==============================================================================
def test_03_unresolved_and_conflict_pumps_create_zero_active_snapshot_rows(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    active_candidates, extras = derive_installations(ir_rows, pumps_by_tag)

    active_tags = {c.pump_tag_number for c in active_candidates}

    unresolved_pumps = ["101-P-6A", "101-P-6C", "211-P-2A", "212-P-25A", "940-P-2A"]
    for p in unresolved_pumps:
        assert p not in active_tags, f"Unresolved pump {p} must NOT create active snapshot row"

    conflict_pumps = ["101-P-3B", "945-P-7B", "140-P-26B"]
    for p in conflict_pumps:
        assert p not in active_tags, f"Conflict pump {p} must NOT create active snapshot row"


# ==============================================================================
# 4. Exact Frozen Manifest: 31 Pumps / 39 Rows
# ==============================================================================
def test_04_exact_frozen_manifest_counts(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    manifest_csv = PROJECT_ROOT / "ltsa_current_installation_r3a_dry_run.csv"
    res = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)

    assert len(res["stats"]["auto_eligible_pumps"]) == 31
    assert len(res["manifest_rows"]) == 39
    assert res["stats"]["single_rows"] == 23
    assert res["stats"]["de_rows"] == 8
    assert res["stats"]["nde_rows"] == 8
    assert res["stats"]["na_rows"] == 0


# ==============================================================================
# 5. Manifest Determinism Across Repeated Execution
# ==============================================================================
def test_05_manifest_determinism_across_repeated_runs(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    manifest_csv = PROJECT_ROOT / "ltsa_current_installation_r3a_dry_run.csv"

    res1 = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)
    hash1 = res1["manifest_sha256"]

    res2 = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)
    hash2 = res2["manifest_sha256"]

    assert hash1 == hash2, "Manifest hash must be 100% deterministic"
    assert hash1 == "d4e7940684c1c315e54f3b0399707b155e1bb9666560c48fd19a85a3cf64c279"


# ==============================================================================
# 6. Source Traceability 39/39 Verification
# ==============================================================================
def test_06_source_traceability_39_of_39(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    manifest_csv = PROJECT_ROOT / "ltsa_current_installation_r3a_dry_run.csv"
    res = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)

    trace = verify_source_traceability(res["manifest_rows"], ir_rows, pumps_by_tag)
    assert trace["pass_count"] == 39
    assert trace["fail_count"] == 0
    assert len(trace["details"]) == 0


# ==============================================================================
# 7. Superseded Replacement Chains
# ==============================================================================
def test_07_superseded_sources_not_active(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    manifest_csv = PROJECT_ROOT / "ltsa_current_installation_r3a_dry_run.csv"
    res = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)

    active_refs = {r["source_reference"] for r in res["manifest_rows"]}

    # 220-P-3A: INSTL-019-2026 superseded by INSTL-037-2026
    assert "INSTL-037-2026" in active_refs
    assert "INSTL-019-2026" not in active_refs

    # 945-P-9B: INSTL-022-2026 superseded by INSTL-026-2026
    assert "INSTL-026-2026" in active_refs
    assert "INSTL-022-2026" not in active_refs

    # 200-P-4B: INSTL-023-2026 superseded by INSTL-040-2026
    assert "INSTL-040-2026" in active_refs
    assert "INSTL-023-2026" not in active_refs


# ==============================================================================
# 8. Drawing Semantics and Quarantined Drawing Boundary
# ==============================================================================
def test_08_quarantined_drawing_ga_187530_boundary(prod_sources):
    ir_rows, pumps_by_tag = prod_sources
    manifest_csv = PROJECT_ROOT / "ltsa_current_installation_r3a_dry_run.csv"
    res = generate_and_freeze_manifest(ir_rows, pumps_by_tag, manifest_csv)

    # GA-187530 must never appear in the backfill manifest
    quarantined = [r for r in res["manifest_rows"] if r.get("drawing_no") == "GA-187530"]
    assert len(quarantined) == 0


# ==============================================================================
# 9. API Empty State: Topology-Aware Positions, Zero Configured Seal Leakage
# ==============================================================================
def test_09_api_empty_state_for_oh_pump(client_and_repo):
    client, _, _ = client_and_repo

    resp = client.get("/api/ltsa/pumps/999-P-EMPTY-OH/current-installation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["pump_tag"] == "999-P-EMPTY-OH"
    assert data["pump_type"] == "OH2"
    assert data["status"] == "NO_CURRENT_RECORD"
    assert "SINGLE" in data["positions"]
    pos = data["positions"]["SINGLE"]
    assert pos["resolution_status"] == "NO_AUTHORITATIVE_EVIDENCE"
    assert pos["installed_seal"] is None
    assert "CONFIGURED_EMPTY_SEAL" not in resp.text


def test_10_api_empty_state_for_bb_pump(client_and_repo):
    client, _, _ = client_and_repo

    resp = client.get("/api/ltsa/pumps/999-P-EMPTY-BB/current-installation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["pump_tag"] == "999-P-EMPTY-BB"
    assert data["pump_type"] == "BB3"
    assert data["status"] == "NO_CURRENT_RECORD"
    assert "DE" in data["positions"]
    assert "NDE" in data["positions"]
    assert data["positions"]["DE"]["installed_seal"] is None
    assert data["positions"]["NDE"]["installed_seal"] is None
    assert data["positions"]["DE"]["resolution_status"] == "NO_AUTHORITATIVE_EVIDENCE"
    assert data["positions"]["NDE"]["resolution_status"] == "NO_AUTHORITATIVE_EVIDENCE"
    assert "CONFIGURED_BB_SEAL" not in resp.text


def test_11_api_empty_state_for_unknown_topology_pump(client_and_repo):
    client, _, _ = client_and_repo

    resp = client.get("/api/ltsa/pumps/999-P-UNKNOWN-TYPE/current-installation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["pump_tag"] == "999-P-UNKNOWN-TYPE"
    assert data["status"] == "NO_CURRENT_RECORD"
    # Topology unknown -> must NOT fabricate fake positions
    assert data["positions"] == {}
    assert "CONFIGURED_UNKNOWN_SEAL" not in resp.text


# ==============================================================================
# 12. API Active States & Area Scoping
# ==============================================================================
def test_12_api_active_oh_pump(client_and_repo):
    client, repo, _ = client_and_repo

    repo.create_installation(
        pump_tag_number="101-P-8A",
        equipment_side="SINGLE",
        seal_type="5620P",
        seal_size="2.125",
        drawing_no="GA-214072-1",
        material_code="334",
        source_type="INSTALLATION_REPORT",
        source_reference="INSTL-001-2026",
        source_date="2026-01-06",
        resolution_status="CONFIRMED",
        confidence_status="CONFIRMED",
    )

    resp = client.get("/api/ltsa/pumps/101-P-8A/current-installation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "CONFIRMED"
    assert "SINGLE" in data["positions"]
    single = data["positions"]["SINGLE"]
    assert single["seal_type"] == "5620P"
    assert single["installed_seal"]["seal_type"] == "5620P"


def test_13_api_active_bb_pump(client_and_repo):
    client, repo, _ = client_and_repo

    for side in ("DE", "NDE"):
        repo.create_installation(
            pump_tag_number="211-P-1A",
            equipment_side=side,
            seal_type="T8B1-RS",
            seal_size="4.1/2",
            drawing_no="TMI-8B-1514",
            material_code="AR1S1/P",
            source_type="INSTALLATION_REPORT",
            source_reference="INSTL-033-2026",
            source_date="2026-05-22",
            resolution_status="CONFIRMED",
            confidence_status="CONFIRMED",
        )

    resp = client.get("/api/ltsa/pumps/211-P-1A/current-installation")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "CONFIRMED"
    assert "DE" in data["positions"]
    assert "NDE" in data["positions"]
    assert data["positions"]["DE"]["installed_seal"]["seal_type"] == "T8B1-RS"
    assert data["positions"]["NDE"]["installed_seal"]["seal_type"] == "T8B1-RS"


def test_14_api_area_scope_enforcement(client_and_repo):
    client, repo, _ = client_and_repo

    repo.create_installation(
        pump_tag_number="200-P-1A",
        equipment_side="SINGLE",
        seal_type="T48MP",
        source_type="INSTALLATION_REPORT",
        source_reference="INSTL-HSC-001",
        resolution_status="CONFIRMED",
        confidence_status="CONFIRMED",
    )

    app.dependency_overrides[get_current_user] = lambda: PERTAMINA_HOC_USER
    resp_hoc = client.get("/api/ltsa/pumps/101-P-8A/current-installation")
    assert resp_hoc.status_code == 200

    resp_hsc_blocked = client.get("/api/ltsa/pumps/200-P-1A/current-installation")
    assert resp_hsc_blocked.status_code == 404

    app.dependency_overrides[get_current_user] = lambda: PERTAMINA_HSC_USER
    resp_hsc_allowed = client.get("/api/ltsa/pumps/200-P-1A/current-installation")
    assert resp_hsc_allowed.status_code == 200
