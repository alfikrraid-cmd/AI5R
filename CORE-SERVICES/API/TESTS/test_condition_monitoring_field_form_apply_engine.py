"""AI5R — LTSA Condition Monitoring Field Form Atomic Apply Engine Tests (CM R5E.4).

Unit tests and real-DB atomicity tests validating:
- Deterministic content hashing and identity
- Reviewer/applier independence
- Quarantined asset rejection (946-P-2D, 946-P-4A, 946-P-4C, 946-P-8A, 946-P-8B)
- Blank asset skipping (SKIPPED_BLANK)
- Pure NI/NA skipping (SKIPPED_NOT_INSPECTED)
- 42 Canonical mapping (20 legacy + 20 measurement + 2 observation)
- Zero vs N/A distinction
- Zero finding creation
- Real-DB:
  A. Synthetic per-asset insert (parent + measurements + audit in ONE transaction)
  B. Forced measurement failure -> parent rollback
  C. Forced audit failure -> parent + measurements rollback
  D. Idempotency & duplicate source_reference handling
  E. Soft-delete reapply behavior with migration 041
  F. Zero ltsa_finding creation
  G. TEST_BUSINESS_ROWS_PERSISTED = 0
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

API_PATH = Path(__file__).resolve().parents[1]
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

from condition_monitoring_field_form_engine import (  # noqa: E402
    _PARAM_CONTRACTS,
    ParsedValue,
    StorageTier,
    ValueState,
    ConditionState,
    get_parameter_contract,
    parse_field_value,
)

from condition_monitoring_field_form_apply_engine import (  # noqa: E402
    ApplyOutcome,
    QUARANTINED_ASSET_CODES,
    LEGACY_MAPPING_COUNT,
    MEASUREMENT_MAPPING_COUNT,
    OBSERVATION_MAPPING_COUNT,
    TOTAL_CANONICAL_PARAMETERS,
    build_content_payload,
    compute_content_hash,
    build_approval_binding,
    compute_approval_binding_hash,
    check_apply_eligibility,
    format_source_reference,
    validate_approval,
    apply_asset_reading_atomic,
    apply_batch_orchestrator,
)


# ==============================================================================
# 1. UNIT TESTS: CONTENT IDENTITY & HASHING
# ==============================================================================

def test_content_hash_determinism():
    payload_1 = build_content_payload(
        canonical_asset="211-P-13AR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13A",
        parameter_values={"suction_pressure": 2.5, "discharge_temp": 45.0},
        units={"suction_pressure": "kg/cm2", "discharge_temp": "°C"},
        condition_states={"suction_pressure": "NORMAL", "discharge_temp": "NORMAL"},
    )
    # Different order of parameters input
    payload_2 = build_content_payload(
        canonical_asset="211-P-13AR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13A",
        parameter_values={"discharge_temp": 45.0, "suction_pressure": 2.5},
        units={"discharge_temp": "°C", "suction_pressure": "kg/cm2"},
        condition_states={"discharge_temp": "NORMAL", "suction_pressure": "NORMAL"},
    )

    hash_1 = compute_content_hash(payload_1)
    hash_2 = compute_content_hash(payload_2)

    assert hash_1 == hash_2
    assert len(hash_1) == 64


def test_reviewer_and_applier_independence():
    # Content payload excludes reviewer, applier, timestamps
    payload = build_content_payload(
        canonical_asset="211-P-13AR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13A",
        parameter_values={"suction_pressure": 2.5},
    )
    hash_base = compute_content_hash(payload)

    # Verifying approval binding binds content hash to reviewer, but content hash itself is invariant
    binding_reviewer_a = build_approval_binding(
        content_hash=hash_base,
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        reviewed_by="reviewer-uuid-1",
        reviewed_at="2026-09-06T10:00:00Z",
        review_decision="ACCEPTED_FOR_FUTURE_APPLY",
    )
    binding_reviewer_b = build_approval_binding(
        content_hash=hash_base,
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        reviewed_by="reviewer-uuid-2",
        reviewed_at="2026-09-06T11:00:00Z",
        review_decision="ACCEPTED_FOR_FUTURE_APPLY",
    )

    # Content hash remains unchanged
    assert binding_reviewer_a["content_hash"] == hash_base
    assert binding_reviewer_b["content_hash"] == hash_base
    # Approval binding hash differs between reviewers
    assert compute_approval_binding_hash(binding_reviewer_a) != compute_approval_binding_hash(binding_reviewer_b)


def test_content_hash_mismatch_detected():
    base_payload = build_content_payload(
        canonical_asset="211-P-13AR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13A",
        parameter_values={"suction_pressure": 2.5},
    )
    base_hash = compute_content_hash(base_payload)

    # Altering parameter value alters hash
    payload_val_changed = build_content_payload(
        canonical_asset="211-P-13AR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13A",
        parameter_values={"suction_pressure": 2.6},
    )
    assert compute_content_hash(payload_val_changed) != base_hash

    # Altering canonical asset alters hash
    payload_asset_changed = build_content_payload(
        canonical_asset="211-P-13BR",
        inspection_date="2026-09-06",
        workbook_sha256="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        source_sheet="RX 211",
        source_asset_literal="211-P-13B",
        parameter_values={"suction_pressure": 2.5},
    )
    assert compute_content_hash(payload_asset_changed) != base_hash


# ==============================================================================
# 2. UNIT TESTS: ELIGIBILITY & QUARANTINE
# ==============================================================================

def test_quarantined_assets_strictly_rejected():
    # All 5 quarantined assets must be rejected even with valid values
    for q_asset in QUARANTINED_ASSET_CODES:
        contract = get_parameter_contract("suction_pressure")
        assert contract is not None
        pv = parse_field_value(3.5, contract)
        is_eligible, outcome = check_apply_eligibility(q_asset, {"suction_pressure": pv})
        assert not is_eligible
        assert outcome == ApplyOutcome.REJECTED_QUARANTINE


def test_blank_asset_skipped():
    contract = get_parameter_contract("suction_pressure")
    assert contract is not None
    pv = parse_field_value(None, contract)
    is_eligible, outcome = check_apply_eligibility("211-P-13AR", {"suction_pressure": pv})
    assert not is_eligible
    assert outcome == ApplyOutcome.SKIPPED_BLANK


def test_not_inspected_pure_asset_skipped():
    contract = get_parameter_contract("suction_pressure")
    assert contract is not None
    pv = parse_field_value("NI", contract)
    is_eligible, outcome = check_apply_eligibility("211-P-13AR", {"suction_pressure": pv})
    assert not is_eligible
    assert outcome == ApplyOutcome.SKIPPED_NOT_INSPECTED


def test_zero_is_preserved_and_eligible():
    contract = get_parameter_contract("suction_pressure")
    assert contract is not None
    # 0.0 is meaningful inspection value (e.g. 0 pressure or vibration)
    pv = parse_field_value(0.0, contract)
    assert pv.value_state == ValueState.VALUE_PRESENT
    assert pv.normalized_value == 0.0

    is_eligible, outcome = check_apply_eligibility("211-P-13AR", {"suction_pressure": pv})
    assert is_eligible
    assert outcome == ApplyOutcome.APPLIED


def test_zero_vs_na_distinction():
    contract = get_parameter_contract("suction_pressure")
    assert contract is not None
    pv_zero = parse_field_value(0, contract)
    pv_na = parse_field_value("N/A", contract)
    pv_ni = parse_field_value("NI", contract)

    assert pv_zero.value_state == ValueState.VALUE_PRESENT
    assert pv_zero.normalized_value == 0.0

    assert pv_na.value_state == ValueState.NOT_APPLICABLE
    assert pv_na.normalized_value is None

    assert pv_ni.value_state == ValueState.NOT_INSPECTED
    assert pv_ni.normalized_value is None


def test_canonical_mapping_counts():
    assert TOTAL_CANONICAL_PARAMETERS == 42
    assert LEGACY_MAPPING_COUNT == 20
    assert MEASUREMENT_MAPPING_COUNT == 20
    assert OBSERVATION_MAPPING_COUNT == 2

    legacy = [p for p in _PARAM_CONTRACTS if p.storage_tier == StorageTier.LEGACY_PARENT_TABLE]
    meas = [p for p in _PARAM_CONTRACTS if p.storage_tier == StorageTier.CHILD_MEASUREMENT_TABLE]
    obs = [p for p in _PARAM_CONTRACTS if p.storage_tier == StorageTier.CHILD_OBSERVATION_TABLE]

    assert len(legacy) == 20
    assert len(meas) == 20
    assert len(obs) == 2


def test_idempotency_source_reference_format():
    ref = format_source_reference(
        full_workbook_sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        inspection_date="2026-09-06",
        canonical_asset="211-P-13AR",
    )
    assert ref == "field_form:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890:2026-09-06:211-P-13AR"


def test_approval_validation_contract():
    valid_preview = {
        "preview_id": "test-preview-01",
        "expired": False,
        "review_decision": "ACCEPTED_FOR_FUTURE_APPLY",
        "workbook_sha256": "wb_hash_01",
        "content_hash": "content_hash_01",
    }
    # Success case
    ok, err = validate_approval(
        preview_session=valid_preview,
        asset_content_hash="content_hash_01",
        expected_workbook_sha256="wb_hash_01",
        actor_id="actor-01",
        actor_permissions={"maintenance.write"},
        actor_area_scope={"HOC"},
        asset_area="HOC",
    )
    assert ok
    assert err is None

    # Missing maintenance.write permission
    ok, err = validate_approval(
        preview_session=valid_preview,
        asset_content_hash="content_hash_01",
        expected_workbook_sha256="wb_hash_01",
        actor_id="actor-01",
        actor_permissions={"maintenance.read"},
        actor_area_scope={"HOC"},
        asset_area="HOC",
    )
    assert not ok
    assert err == ApplyOutcome.AUTH_DENIED.value

    # Area scope mismatch
    ok, err = validate_approval(
        preview_session=valid_preview,
        asset_content_hash="content_hash_01",
        expected_workbook_sha256="wb_hash_01",
        actor_id="actor-01",
        actor_permissions={"maintenance.write"},
        actor_area_scope={"HSC"},
        asset_area="HOC",
    )
    assert not ok
    assert err == ApplyOutcome.AREA_SCOPE_DENIED.value

    # R5D integration gap case: preview lacks content_hash
    preview_missing_hash = {
        "preview_id": "test-preview-02",
        "expired": False,
        "review_decision": "ACCEPTED_FOR_FUTURE_APPLY",
        "workbook_sha256": "wb_hash_01",
    }
    ok, err = validate_approval(
        preview_session=preview_missing_hash,
        asset_content_hash="content_hash_01",
        expected_workbook_sha256="wb_hash_01",
        actor_id="actor-01",
        actor_permissions={"maintenance.write"},
        actor_area_scope={"HOC"},
        asset_area="HOC",
    )
    assert not ok
    assert err == "R5D_CONTENT_HASH_MISSING"


# ==============================================================================
# 3. REAL-DB ATOMICITY TESTS (LOCAL ltsa_brain ONLY)
# ==============================================================================

class DockerExecRunner:
    def __init__(self, container: str = "ai5r-runtime-postgres-1", user: str = "ai5r", db: str = "ltsa_brain"):
        self.container = container
        self.user = user
        self.db = db

    def query_scalar(self, sql: str) -> str:
        res = subprocess.run(
            [
                "docker", "exec", "-i", self.container,
                "psql", "-U", self.user, "-d", self.db,
                "-v", "ON_ERROR_STOP=1", "-tAc", sql,
            ],
            capture_output=True, text=True, check=True,
        )
        return res.stdout.strip()

    def execute_script(self, sql: str) -> None:
        subprocess.run(
            [
                "docker", "exec", "-i", self.container,
                "psql", "-U", self.user, "-d", self.db,
                "-v", "ON_ERROR_STOP=1", "-c", sql,
            ],
            capture_output=True, text=True, check=True,
        )


def _check_docker_postgres_available() -> bool:
    try:
        runner = DockerExecRunner()
        res = runner.query_scalar("SELECT 1;")
        return res == "1"
    except Exception:
        return False


_HAS_LOCAL_DB = _check_docker_postgres_available()


@pytest.fixture
def db_runner():
    if not _HAS_LOCAL_DB:
        pytest.skip("Local docker postgres container ai5r-runtime-postgres-1 not accessible")
    runner = DockerExecRunner()
    yield runner
    # Clean up any leftover synthetic test data
    runner.execute_script("""
        DELETE FROM condition_monitoring_reading_measurement 
        WHERE source_reference LIKE 'field_form:synthetic_%';
        DELETE FROM record_change_history 
        WHERE source_reference LIKE 'field_form:synthetic_%';
        DELETE FROM condition_monitoring_reading 
        WHERE source_reference LIKE 'field_form:synthetic_%';
    """)


def _build_synthetic_42_parameters() -> dict[str, ParsedValue]:
    parsed: dict[str, ParsedValue] = {}
    for contract in _PARAM_CONTRACTS:
        if contract.storage_tier == StorageTier.LEGACY_PARENT_TABLE:
            val = False if contract.data_type == "BOOLEAN" else 42.0
        elif contract.storage_tier == StorageTier.CHILD_MEASUREMENT_TABLE:
            val = 55.5
        else:
            val = "OBSERVED_NORMAL"
        pv = parse_field_value(val, contract)
        parsed[contract.code] = pv
    return parsed


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_a_successful_per_asset_atomic_persistence(db_runner):
    """A. successful synthetic per-asset transaction can insert: parent + measurements + audit."""
    synthetic_hash = "synthetic_hash_a_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"
    parsed_items = _build_synthetic_42_parameters()

    res = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
    )

    assert res["outcome"] == ApplyOutcome.APPLIED.value
    reading_code = res["reading_code"]
    assert reading_code is not None
    assert res["measurements_inserted"] == 20
    assert res["observations_inserted"] == 2
    assert res["audit_logged"] is True

    # Verify parent reading row in DB
    cnt_parent = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE condition_monitoring_reading_code = '{reading_code}';"
    ))
    assert cnt_parent == 1

    # Verify child measurements in DB
    cnt_meas = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading_measurement WHERE reading_id = '{reading_code}';"
    ))
    assert cnt_meas == 22  # 20 measurements + 2 observations

    # Verify audit entry in DB
    cnt_audit = int(db_runner.query_scalar(
        f"SELECT count(*) FROM record_change_history WHERE entity_id = '{reading_code}';"
    ))
    assert cnt_audit == 1

    # Verify NO ltsa_finding was created
    cnt_finding = int(db_runner.query_scalar(
        f"SELECT count(*) FROM ltsa_finding WHERE source_record_code = '{reading_code}';"
    ))
    assert cnt_finding == 0


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_b_forced_measurement_failure_rolls_back_parent(db_runner):
    """B. forced measurement failure rolls back parent reading completely."""
    synthetic_hash = "synthetic_hash_b_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"
    parsed_items = _build_synthetic_42_parameters()

    res = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
        force_measurement_failure=True,  # triggers check constraint failure
    )

    assert res["outcome"] == ApplyOutcome.MEASUREMENT_INSERT_FAILURE.value
    expected_ref = format_source_reference(
        full_workbook_sha256=synthetic_hash,
        inspection_date=inspection_date,
        canonical_asset=canonical_asset,
    )

    # Prove parent reading was NOT persisted in DB
    cnt_parent = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_parent == 0

    # Prove measurements were NOT persisted in DB
    cnt_meas = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading_measurement WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_meas == 0

    # Prove audit was NOT persisted in DB
    cnt_audit = int(db_runner.query_scalar(
        f"SELECT count(*) FROM record_change_history WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_audit == 0


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_c_forced_audit_failure_rolls_back_parent_and_measurements(db_runner):
    """C. forced audit failure rolls back parent + measurements completely."""
    synthetic_hash = "synthetic_hash_c_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"
    parsed_items = _build_synthetic_42_parameters()

    res = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
        force_audit_failure=True,  # triggers NOT NULL violation on entity_type
    )

    assert res["outcome"] == ApplyOutcome.AUDIT_INSERT_FAILURE.value
    expected_ref = format_source_reference(
        full_workbook_sha256=synthetic_hash,
        inspection_date=inspection_date,
        canonical_asset=canonical_asset,
    )

    # Prove parent reading was NOT persisted
    cnt_parent = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_parent == 0

    # Prove measurements were NOT persisted
    cnt_meas = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading_measurement WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_meas == 0


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_d_duplicate_source_reference_rejected_safely(db_runner):
    """D. duplicate source_reference is identified and rejected / returned safely as ALREADY_APPLIED."""
    synthetic_hash = "synthetic_hash_d_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"
    parsed_items = _build_synthetic_42_parameters()

    # First apply -> APPLIED
    res1 = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
    )
    assert res1["outcome"] == ApplyOutcome.APPLIED.value
    reading_code_1 = res1["reading_code"]

    # Second apply with exact same identity -> ALREADY_APPLIED
    res2 = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
    )
    assert res2["outcome"] == ApplyOutcome.ALREADY_APPLIED.value
    assert res2["reading_code"] == reading_code_1

    # Verify still exactly 1 reading row exists in DB
    expected_ref = format_source_reference(
        full_workbook_sha256=synthetic_hash,
        inspection_date=inspection_date,
        canonical_asset=canonical_asset,
    )
    cnt = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt == 1


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_e_soft_delete_reapply_allowed(db_runner):
    """E. soft-deleted previous identity allows re-apply per migration 041 index."""
    synthetic_hash = "synthetic_hash_e_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"
    parsed_items = _build_synthetic_42_parameters()

    # 1. First apply
    res1 = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
    )
    assert res1["outcome"] == ApplyOutcome.APPLIED.value
    reading_code_1 = res1["reading_code"]

    # 2. Soft-delete the reading
    expected_ref = format_source_reference(
        full_workbook_sha256=synthetic_hash,
        inspection_date=inspection_date,
        canonical_asset=canonical_asset,
    )
    db_runner.execute_script(
        f"UPDATE condition_monitoring_reading SET deleted_at = NOW() WHERE condition_monitoring_reading_code = '{reading_code_1}';"
    )

    # 3. Re-apply should succeed because migration 041 unique index specifies WHERE deleted_at IS NULL
    res2 = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items=parsed_items,
    )
    assert res2["outcome"] == ApplyOutcome.APPLIED.value
    reading_code_2 = res2["reading_code"]
    assert reading_code_2 != reading_code_1

    # Verify in DB: 2 rows total, but only 1 active row
    cnt_total = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference = '{expected_ref}';"
    ))
    assert cnt_total == 2

    cnt_active = int(db_runner.query_scalar(
        f"SELECT count(*) FROM condition_monitoring_reading WHERE source_reference = '{expected_ref}' AND deleted_at IS NULL;"
    ))
    assert cnt_active == 1


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_f_zero_findings_created(db_runner):
    """F. verify no ltsa_finding is created even when abnormal condition is parsed."""
    synthetic_hash = "synthetic_hash_f_00000000000000000000000000000000000000000000000000"
    canonical_asset = "211-P-13AR"
    inspection_date = "2026-09-06"

    # Leak observed -> flagged abnormal condition, but must NEVER create ltsa_finding
    contract_leak = get_parameter_contract("mechanical_seal_leak_de")
    assert contract_leak is not None
    pv_leak = parse_field_value(True, contract_leak)
    assert pv_leak.condition == ConditionState.ABNORMAL

    res = apply_asset_reading_atomic(
        db_runner,
        canonical_asset=canonical_asset,
        inspection_date=inspection_date,
        full_workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        source_asset_literal="211-P-13AR",
        parsed_items={"mechanical_seal_leak_de": pv_leak},
    )
    assert res["outcome"] == ApplyOutcome.APPLIED.value
    reading_code = res["reading_code"]

    cnt_finding = int(db_runner.query_scalar(
        f"SELECT count(*) FROM ltsa_finding WHERE source_record_code = '{reading_code}';"
    ))
    assert cnt_finding == 0


@pytest.mark.skipif(not _HAS_LOCAL_DB, reason="Requires running local ltsa_brain")
def test_real_db_test_g_batch_orchestrator_and_zero_rows_persisted_final(db_runner):
    """G. batch orchestrator produces deterministic outcomes and test cleans all synthetic rows."""
    synthetic_hash = "synthetic_hash_batch_0000000000000000000000000000000000000000000000"
    inspection_date = "2026-09-06"

    contract_p = get_parameter_contract("suction_pressure")
    assert contract_p is not None
    pv_valid = parse_field_value(3.5, contract_p)
    pv_blank = parse_field_value(None, contract_p)
    pv_ni = parse_field_value("NI", contract_p)

    batch = [
        # 1. Eligible asset
        {"canonical_asset": "211-P-13AR", "parsed_items": {"suction_pressure": pv_valid}},
        # 2. Blank asset
        {"canonical_asset": "211-P-13BR", "parsed_items": {"suction_pressure": pv_blank}},
        # 3. NI asset
        {"canonical_asset": "211-P-14A", "parsed_items": {"suction_pressure": pv_ni}},
        # 4. Quarantined asset
        {"canonical_asset": "946-P-2D", "parsed_items": {"suction_pressure": pv_valid}},
    ]

    summary = apply_batch_orchestrator(
        db_runner,
        workbook_sha256=synthetic_hash,
        source_sheet="RX 211",
        inspection_date=inspection_date,
        asset_batch=batch,
    )

    assert summary.total_assets == 4
    assert summary.applied_count == 1
    assert summary.skipped_blank_count == 1
    assert summary.skipped_ni_count == 1
    assert summary.rejected_quarantine_count == 1
    assert summary.failed_count == 0

    # Cleanup synthetic rows
    db_runner.execute_script("""
        DELETE FROM condition_monitoring_reading_measurement 
        WHERE source_reference LIKE 'field_form:synthetic_%';
        DELETE FROM record_change_history 
        WHERE source_reference LIKE 'field_form:synthetic_%';
        DELETE FROM condition_monitoring_reading 
        WHERE source_reference LIKE 'field_form:synthetic_%';
    """)

    # Verify final business rows persisted = 0
    cnt_leftover = int(db_runner.query_scalar(
        "SELECT count(*) FROM condition_monitoring_reading WHERE source_reference LIKE 'field_form:synthetic_%';"
    ))
    assert cnt_leftover == 0

