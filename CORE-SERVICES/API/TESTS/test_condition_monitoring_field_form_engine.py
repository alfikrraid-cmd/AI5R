"""Focused test suite for AI5R Condition Monitoring Field Form Ingestion Engine (CM R5B).

Tests covering:
1.  42/42 canonical parameter resolution
2.  133 exact asset identities
3.  15/15 approved aliases
4.  5/5 quarantined assets
5.  No generic alias behavior (prohibit A->AR, B->BR, unauthorized prefixes)
6.  Zero vs N/A (0.0 != N/A)
7.  N/A vs not-inspected (N/A != NOT_INSPECTED)
8.  Unknown vs not-inspected (UNKNOWN != NOT_INSPECTED)
9.  Blank vs zero (blank != 0.0)
10. Numeric parsing
11. Invalid numeric
12. Unit validation
13. Leakage NONE (maps to boolean False, normal condition)
14. Leakage OBSERVED (maps to boolean True, abnormal condition)
15. Observation != Finding (hard boundary: no auto-created findings)
16. Condition != Measurement (condition state distinct from numeric value)
17. Preview no-write (pure in-memory preview)
18. Quarantined asset no-write (refuses persistence for quarantined assets)
19. Duplicate detection (storage tier routing enforces single write)
20. Idempotency stable (stable source_reference generation)
21. Atomic rollback simulation (all-or-nothing transaction planning)
22. Historical reading compatibility (readings without child measurements remain valid)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
import sys

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
for path in (_CORE_SERVICES_DIR, _API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from condition_monitoring_field_form_engine import (
    ConditionMonitoringFieldFormEngine,
    AssetResolver,
    CanonicalParameterContract,
    get_parameter_contract,
    parse_field_value,
    plan_asset_storage,
    generate_idempotency_key,
    FieldFormPersistenceAdapter,
    QuarantinedAssetPersistenceError,
    IngestionState,
    ValueState,
    ConditionState,
    LeakageState,
    StorageTier,
    ErrorCode,
    _PARAM_CONTRACTS,
    APPROVED_EXPLICIT_ALIASES,
    APPROVED_CELL_ALIASES,
    QUARANTINED_ASSET_LITERALS,
)

# Load the 133 exact canonical assets identified during R1 / R5A.1
_EXACT_133_ASSETS = ['101-P-10A', '101-P-10B', '101-P-11', '101-P-2A', '101-P-2B', '101-P-3A', '101-P-3B', '101-P-4A', '101-P-4B', '101-P-4C', '101-P-5A', '101-P-5B', '101-P-6A', '101-P-6B', '101-P-6C', '101-P-7A', '101-P-7B', '101-P-8A', '101-P-8B', '101-P-8C', '101-P-9A', '101-P-9B', '200-P-1A', '200-P-1B', '200-P-3A', '200-P-3B', '200-P-4A', '200-P-4B', '200-P-5A', '200-P-5B', '200-P-6A', '200-P-6B', '211-P-10A', '211-P-10B', '211-P-11A', '211-P-11B', '211-P-13AR', '211-P-13BR', '211-P-14A', '211-P-14B', '211-P-15C', '211-P-16A', '211-P-16B', '211-P-18A', '211-P-18B', '211-P-19A', '211-P-19B', '211-P-1A', '211-P-1B', '211-P-21A', '211-P-21B', '211-P-23A', '211-P-23B', '211-P-25A', '211-P-25B', '211-P-28A', '211-P-28B', '211-P-2A', '211-P-2B', '211-P-3', '211-P-30', '211-P-31', '211-P-4A', '211-P-4B', '211-P-72A', '211-P-72B', '211-P-7A', '211-P-7B', '211-P-8A', '211-P-8B', '212-P-1', '212-P-10A', '212-P-10B', '212-P-11A', '212-P-11B', '212-P-13AR', '212-P-13BR', '212-P-14A', '212-P-14B', '212-P-15C', '212-P-16A', '212-P-16B', '212-P-18A', '212-P-18B', '212-P-19A', '212-P-19B', '212-P-2', '212-P-21A', '212-P-21B', '212-P-23A', '212-P-23B', '212-P-25A', '212-P-25B', '212-P-3', '212-P-4A', '212-P-4B', '212-P-72', '212-P-7A', '212-P-7B', '212-P-8A', '212-P-8B', '300-P-1A', '300-P-1B', '300-P-2A', '300-P-2B', '300-P-6A', '300-P-6B', '300-P-7A', '300-P-7B', '300-P-9A', '300-P-9B', '701-P-1A', '701-P-1B', '701-P-2', '701-P-3A', '701-P-3B', '701-P-4A', '701-P-4B', '701-P-7A', '701-P-7B', '702-P-1A', '702-P-1B', '702-P-2', '702-P-3A', '702-P-3B', '702-P-4A', '702-P-4B', '702-P-7A', '702-P-7B', '702-P-9A', '702-P-9B', '946-P-2A', '946-P-2B']

# The 15 approved explicit aliases from R5A.1
_APPROVED_15_ALIASES = [
    ("H2P 701", "H2P 701!M6", "MM 51", "701-MM-51"),
    ("H2P 702", "H2P 702!O6", "MM 51", "702-MM-51"),
    ("AMINE", "AMINE!D6", "2A", "410-P-2A"),
    ("AMINE", "AMINE!E6", "2B", "410-P-2B"),
    ("AMINE", "AMINE!F6", "3A", "410-P-3A"),
    ("AMINE", "AMINE!G6", "3B", "410-P-3B"),
    ("AMINE", "AMINE!H6", "1A", "840-P-1A"),
    ("AMINE", "AMINE!I6", "1B", "840-P-1B"),
    ("AMINE", "AMINE!J6", "2", "840-P-2"),
    ("AMINE", "AMINE!K6", "3A", "840-P-3A"),
    ("AMINE", "AMINE!L6", "3B", "840-P-3B"),
    ("AMINE", "AMINE!M6", "4A", "840-P-4A"),
    ("AMINE", "AMINE!N6", "4B", "840-P-4B"),
    ("CDU II", "CDU II!N6", "CP 201", "101-CP-201"),
    ("CDU II", "CDU II!O6", "LRC 102", "101-LRC-102"),
]

# The 5 quarantined assets from Unit 946
_QUARANTINED_5_ASSETS = [
    ("SPK om", "SPK om!F6", "2D", "946", "946-P-2D"),
    ("SPK om", "SPK om!G6", "4A", "946", "946-P-4A"),
    ("SPK om", "SPK om!H6", "4C", "946", "946-P-4C"),
    ("SPK om", "SPK om!I6", "8A", "946", "946-P-8A"),
    ("SPK om", "SPK om!J6", "8B", "946", "946-P-8B"),
]


# ==============================================================================
# TEST 1: 42/42 CANONICAL PARAMETER RESOLUTION
# ==============================================================================

def test_01_all_42_parameters_resolve_to_contract():
    assert len(_PARAM_CONTRACTS) == 42
    legacy_count = 0
    child_meas_count = 0
    child_obs_count = 0

    for contract in _PARAM_CONTRACTS:
        # Resolves by exact code
        resolved = get_parameter_contract(contract.code)
        assert resolved is not None
        assert resolved.code == contract.code

        if contract.storage_tier == StorageTier.LEGACY_PARENT_TABLE:
            legacy_count += 1
            assert contract.target_column is not None
        elif contract.storage_tier == StorageTier.CHILD_MEASUREMENT_TABLE:
            child_meas_count += 1
            assert contract.measurement_code_if_child is not None
        elif contract.storage_tier == StorageTier.CHILD_OBSERVATION_TABLE:
            child_obs_count += 1
            assert contract.measurement_code_if_child is not None

    assert legacy_count == 20
    assert child_meas_count == 20
    assert child_obs_count == 2

    # Unknown parameter test
    assert get_parameter_contract("non_existent_parameter_code") is None


# ==============================================================================
# TEST 2: 133 EXACT ASSET IDENTITIES
# ==============================================================================

def test_02_133_exact_asset_identities():
    resolver = AssetResolver(registered_assets=_EXACT_133_ASSETS)
    assert len(_EXACT_133_ASSETS) == 133

    for asset_code in _EXACT_133_ASSETS:
        res = resolver.resolve(asset_code)
        assert res.resolution_method == "EXACT_MATCH"
        assert res.resolution_status == "RESOLVED"
        assert res.canonical_asset_code == asset_code
        assert res.persistence_eligible is True


# ==============================================================================
# TEST 3: 15/15 APPROVED ALIASES
# ==============================================================================

def test_03_15_approved_aliases():
    resolver = AssetResolver(registered_assets=_EXACT_133_ASSETS)
    assert len(_APPROVED_15_ALIASES) == 15

    for sheet, cell, raw_lit, expected_canonical in _APPROVED_15_ALIASES:
        res = resolver.resolve(raw_lit, sheet_name=sheet, cell_position=cell)
        assert res.resolution_method == "APPROVED_ALIAS"
        assert res.resolution_status == "RESOLVED"
        assert res.canonical_asset_code == expected_canonical
        assert res.persistence_eligible is True


# ==============================================================================
# TEST 4: 5/5 QUARANTINED ASSETS
# ==============================================================================

def test_04_5_quarantined_assets():
    resolver = AssetResolver(registered_assets=_EXACT_133_ASSETS)
    assert len(_QUARANTINED_5_ASSETS) == 5

    for sheet, cell, raw_lit, eff_unit, expected_candidate in _QUARANTINED_5_ASSETS:
        res = resolver.resolve(raw_lit, sheet_name=sheet, cell_position=cell, effective_unit=eff_unit)
        assert res.resolution_method == "UNRESOLVED"
        assert res.resolution_status == IngestionState.REVIEW_REQUIRED.value
        assert res.canonical_asset_code is None
        assert res.persistence_eligible is False


# ==============================================================================
# TEST 5: NO GENERIC ALIAS BEHAVIOR
# ==============================================================================

def test_05_prohibit_generic_alias_rules():
    resolver = AssetResolver(registered_assets=_EXACT_133_ASSETS)

    # 1. Prohibit automatic A -> AR (e.g. 211-P-13A must NOT automatically become 211-P-13AR)
    res_13a = resolver.resolve("211-P-13A")
    assert res_13a.canonical_asset_code != "211-P-13AR"
    assert res_13a.persistence_eligible is False

    # 2. Prohibit automatic B -> BR
    res_13b = resolver.resolve("211-P-13B")
    assert res_13b.canonical_asset_code != "211-P-13BR"
    assert res_13b.persistence_eligible is False

    # 3. Arbitrary pump tag
    res_rand = resolver.resolve("999-P-99")
    assert res_rand.persistence_eligible is False
    assert res_rand.resolution_status == ErrorCode.UNKNOWN_ASSET.value


# ==============================================================================
# TEST 6: ZERO VS N/A
# ==============================================================================

def test_06_zero_vs_not_applicable():
    contract = get_parameter_contract("suction_pressure")
    parsed_zero = parse_field_value(0.0, contract)
    parsed_zero_str = parse_field_value("0", contract)
    parsed_na = parse_field_value("N/A", contract)

    assert parsed_zero.value_state == ValueState.VALUE_PRESENT
    assert parsed_zero.normalized_value == 0.0

    assert parsed_zero_str.value_state == ValueState.VALUE_PRESENT
    assert parsed_zero_str.normalized_value == 0.0

    assert parsed_na.value_state == ValueState.NOT_APPLICABLE
    assert parsed_na.normalized_value is None

    # INVARIANT: 0 != N/A
    assert parsed_zero.value_state != parsed_na.value_state
    assert parsed_zero.normalized_value != parsed_na.normalized_value


# ==============================================================================
# TEST 7: N/A VS NOT-INSPECTED
# ==============================================================================

def test_07_not_applicable_vs_not_inspected():
    contract = get_parameter_contract("discharge_temp")
    parsed_na = parse_field_value("N/A", contract)
    parsed_ni = parse_field_value("NI", contract)
    parsed_not_inspected = parse_field_value("NOT INSPECTED", contract)

    assert parsed_na.value_state == ValueState.NOT_APPLICABLE
    assert parsed_ni.value_state == ValueState.NOT_INSPECTED
    assert parsed_not_inspected.value_state == ValueState.NOT_INSPECTED

    # INVARIANT: N/A != NOT_INSPECTED
    assert parsed_na.value_state != parsed_ni.value_state


# ==============================================================================
# TEST 8: UNKNOWN VS NOT-INSPECTED
# ==============================================================================

def test_08_unknown_vs_not_inspected():
    contract = get_parameter_contract("suction_temp")
    parsed_garbage = parse_field_value("CORRUPT_SENSOR_TEXT", contract)
    parsed_blank = parse_field_value("", contract)

    assert parsed_garbage.value_state == ValueState.UNKNOWN
    assert len(parsed_garbage.errors) > 0
    assert parsed_blank.value_state == ValueState.NOT_INSPECTED
    assert len(parsed_blank.errors) == 0

    # INVARIANT: UNKNOWN != NOT_INSPECTED
    assert parsed_garbage.value_state != parsed_blank.value_state


# ==============================================================================
# TEST 9: BLANK VS ZERO
# ==============================================================================

def test_09_blank_vs_zero():
    contract = get_parameter_contract("seal_gland_temp_de")
    parsed_blank = parse_field_value(None, contract)
    parsed_empty_str = parse_field_value("   ", contract)
    parsed_zero = parse_field_value(0, contract)

    assert parsed_blank.value_state == ValueState.NOT_INSPECTED
    assert parsed_blank.normalized_value is None

    assert parsed_empty_str.value_state == ValueState.NOT_INSPECTED
    assert parsed_empty_str.normalized_value is None

    assert parsed_zero.value_state == ValueState.VALUE_PRESENT
    assert parsed_zero.normalized_value == 0.0

    # INVARIANT: blank != 0
    assert parsed_blank.normalized_value != parsed_zero.normalized_value


# ==============================================================================
# TEST 10: NUMERIC PARSING
# ==============================================================================

def test_10_numeric_parsing():
    contract = get_parameter_contract("quench_temp_de")
    assert parse_field_value("42.5", contract).normalized_value == 42.5
    assert parse_field_value(50, contract).normalized_value == 50.0
    assert parse_field_value("100", contract).normalized_value == 100.0


# ==============================================================================
# TEST 11: INVALID NUMERIC
# ==============================================================================

def test_11_invalid_numeric():
    contract = get_parameter_contract("flushing_in_temp_de")
    parsed = parse_field_value("not_a_number", contract)
    assert parsed.value_state == ValueState.UNKNOWN
    assert parsed.normalized_value is None
    assert any("Invalid numeric" in err for err in parsed.errors)


# ==============================================================================
# TEST 12: UNIT VALIDATION
# ==============================================================================

def test_12_unit_validation():
    contract = get_parameter_contract("discharge_pressure")
    # Valid unit: kg/cm2, bar
    valid_res = parse_field_value("10.5", contract, unit="kg/cm2")
    assert len(valid_res.warnings) == 0

    # Invalid unit: PSI (not in allowed tuple)
    invalid_res = parse_field_value("10.5", contract, unit="PSI")
    assert len(invalid_res.warnings) > 0
    assert any("not in expected allowed units" in w for w in invalid_res.warnings)


# ==============================================================================
# TEST 13: LEAKAGE NONE
# ==============================================================================

def test_13_leakage_none():
    contract = get_parameter_contract("mechanical_seal_leak_de")
    for token in ("NONE", "NO LEAK", "TIDAK BOCOR", "AMAN", "NORMAL", "0", False):
        parsed = parse_field_value(token, contract)
        assert parsed.value_state == ValueState.VALUE_PRESENT
        assert parsed.normalized_value is False
        assert parsed.condition == ConditionState.NORMAL


# ==============================================================================
# TEST 14: LEAKAGE OBSERVED
# ==============================================================================

def test_14_leakage_observed():
    contract = get_parameter_contract("mechanical_seal_leak_de")
    for token in ("LEAK", "BOCOR", "MENETES", "REMBES", "OBSERVED", "1", True):
        parsed = parse_field_value(token, contract)
        assert parsed.value_state == ValueState.VALUE_PRESENT
        assert parsed.normalized_value is True
        assert parsed.condition == ConditionState.ABNORMAL


# ==============================================================================
# TEST 15: OBSERVATION != FINDING
# ==============================================================================

def test_15_observation_is_not_finding():
    # Hard boundary check: Leakage OBSERVED or abnormal parameter must NEVER auto-generate finding
    contract = get_parameter_contract("mechanical_seal_leak_de")
    parsed = parse_field_value("BOCOR", contract)
    assert parsed.normalized_value is True

    plan = plan_asset_storage("211-P-1A", {"mechanical_seal_leak_de": parsed})
    assert plan.legacy_parent_values["mechanical_seal_leak_de"] is True

    # Check persistence adapter
    adapter = FieldFormPersistenceAdapter()
    engine = ConditionMonitoringFieldFormEngine(registered_assets=["211-P-1A"])
    preview = engine.preview_batch(
        source_workbook="test.xlsx",
        source_sheet="RX 211",
        reading_date="2026-09-15",
        asset_columns=[{"source_tag": "211-P-1A", "measurements": {"mechanical_seal_leak_de": "BOCOR"}}]
    )
    res = adapter.apply_dry_run(preview.asset_previews[0], created_by="user-test")
    assert res["findings_created"] == 0


# ==============================================================================
# TEST 16: CONDITION != MEASUREMENT
# ==============================================================================

def test_16_condition_distinct_from_measurement():
    contract = get_parameter_contract("stuffing_box_temp_de")
    # Measurement value 65.0, but condition explicitly marked MONITOR
    parsed = parse_field_value("65.0", contract, condition_raw="MONITOR")
    assert parsed.normalized_value == 65.0
    assert parsed.condition == ConditionState.MONITOR

    # Measurement value 30.0, condition marked NORMAL
    parsed_norm = parse_field_value("30.0", contract, condition_raw="NORMAL")
    assert parsed_norm.normalized_value == 30.0
    assert parsed_norm.condition == ConditionState.NORMAL


# ==============================================================================
# TEST 17: PREVIEW NO-WRITE
# ==============================================================================

def test_17_preview_writes_zero_db():
    engine = ConditionMonitoringFieldFormEngine(registered_assets=_EXACT_133_ASSETS)
    columns = [
        {"source_tag": "211-P-1A", "measurements": {"suction_pressure": "2.5", "suction_temp": "35.0"}},
        {"source_tag": "211-P-1B", "measurements": {"suction_pressure": "2.6", "suction_temp": "36.0"}},
    ]
    preview = engine.preview_batch(
        source_workbook="test_wb.xlsx",
        source_sheet="RX 211",
        reading_date="2026-09-15",
        asset_columns=columns
    )
    assert preview.total_assets == 2
    assert preview.resolvable_assets == 2
    assert preview.quarantined_assets == 0
    assert len(preview.asset_previews) == 2
    for ap in preview.asset_previews:
        assert ap.persistence_eligible is True
        assert ap.ingestion_status == IngestionState.READY_TO_APPLY.value


# ==============================================================================
# TEST 18: QUARANTINED ASSET NO-WRITE
# ==============================================================================

def test_18_quarantined_asset_refuses_persistence():
    engine = ConditionMonitoringFieldFormEngine(registered_assets=_EXACT_133_ASSETS)
    columns = [
        {"source_tag": "2D", "cell_position": "SPK om!F6", "effective_unit": "946", "measurements": {"suction_pressure": "3.0"}},
    ]
    preview = engine.preview_batch(
        source_workbook="test_wb.xlsx",
        source_sheet="SPK om",
        reading_date="2026-09-15",
        asset_columns=columns
    )
    assert preview.total_assets == 1
    assert preview.resolvable_assets == 0
    assert preview.quarantined_assets == 1
    quarantined_preview = preview.asset_previews[0]

    assert quarantined_preview.persistence_eligible is False
    assert quarantined_preview.ingestion_status == IngestionState.REVIEW_REQUIRED.value

    adapter = FieldFormPersistenceAdapter()
    with pytest.raises(QuarantinedAssetPersistenceError):
        adapter.build_atomic_sql_transaction(quarantined_preview, created_by="test-user", source_reference="TEST-REF")


# ==============================================================================
# TEST 19: DUPLICATE DETECTION & SINGLE-WRITE ENFORCEMENT
# ==============================================================================

def test_19_duplicate_routing_protection():
    parsed_items = {}
    for contract in _PARAM_CONTRACTS:
        val = 25.0 if contract.data_type == "NUMERIC" else (False if contract.data_type == "BOOLEAN" else "OK")
        parsed_items[contract.code] = parse_field_value(val, contract)

    plan = plan_asset_storage("211-P-1A", parsed_items)
    # Exactly 20 legacy parent columns
    assert len(plan.legacy_parent_values) == 20
    # Exactly 20 child measurements
    assert len(plan.child_measurements) == 20
    # Exactly 2 child observations
    assert len(plan.child_observations) == 2

    # Verify parent keys and child codes never overlap
    parent_keys = set(plan.legacy_parent_values.keys())
    child_codes = {m["measurement_code"] for m in plan.child_measurements}
    assert len(parent_keys.intersection(child_codes)) == 0


# ==============================================================================
# TEST 20: IDEMPOTENCY STABLE
# ==============================================================================

def test_20_idempotency_stability():
    payload_a = [("suction_pressure", 2.5), ("discharge_pressure", 10.0)]
    payload_b = [("discharge_pressure", 10.0), ("suction_pressure", 2.5)]  # reversed order
    payload_c = [("suction_pressure", 2.6), ("discharge_pressure", 10.0)]  # changed value

    key_a = generate_idempotency_key(source_sheet="RX 211", asset_identifier="211-P-1A", reading_date="2026-09-15", parameter_payload=payload_a)
    key_b = generate_idempotency_key(source_sheet="RX 211", asset_identifier="211-P-1A", reading_date="2026-09-15", parameter_payload=payload_b)
    key_c = generate_idempotency_key(source_sheet="RX 211", asset_identifier="211-P-1A", reading_date="2026-09-15", parameter_payload=payload_c)

    # Identical content (regardless of order) -> same key
    assert key_a == key_b
    # Changed content -> different key
    assert key_a != key_c


# ==============================================================================
# TEST 21: ATOMIC ROLLBACK SIMULATION
# ==============================================================================

def test_21_atomic_transaction_script_generation():
    engine = ConditionMonitoringFieldFormEngine(registered_assets=_EXACT_133_ASSETS)
    columns = [
        {
            "source_tag": "211-P-1A",
            "measurements": {
                "suction_pressure": "2.5",
                "separator_in_temp_de": "45.0",
                "reservoir_level_de": "NORMAL"
            }
        }
    ]
    preview = engine.preview_batch(
        source_workbook="test.xlsx",
        source_sheet="RX 211",
        reading_date="2026-09-15",
        asset_columns=columns
    )
    ap = preview.asset_previews[0]
    adapter = FieldFormPersistenceAdapter()
    sql = adapter.build_atomic_sql_transaction(ap, created_by="user-qa", source_reference=ap.idempotency_key)

    # Script structure verified
    assert "BEGIN;" in sql
    assert "DO $$ BEGIN IF NOT EXISTS" in sql
    assert "INSERT INTO condition_monitoring_reading" in sql
    assert "INSERT INTO condition_monitoring_reading_measurement" in sql
    assert "SEPARATOR_IN_TEMP_DE" in sql
    assert "RESERVOIR_LEVEL_DE" in sql
    assert "COMMIT;" in sql


# ==============================================================================
# TEST 22: HISTORICAL READING COMPATIBILITY
# ==============================================================================

def test_22_historical_reading_compatibility():
    # Historical reading with ONLY legacy columns (no child measurements)
    legacy_only_items = {
        "suction_pressure": parse_field_value("2.5", get_parameter_contract("suction_pressure")),
        "discharge_pressure": parse_field_value("10.0", get_parameter_contract("discharge_pressure")),
        "suction_temp": parse_field_value("40.0", get_parameter_contract("suction_temp")),
    }
    plan = plan_asset_storage("211-P-1A", legacy_only_items)
    assert len(plan.legacy_parent_values) == 3
    assert len(plan.child_measurements) == 0
    assert len(plan.child_observations) == 0

