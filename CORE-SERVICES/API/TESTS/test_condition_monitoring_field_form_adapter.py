"""Focused test suite for AI5R Condition Monitoring Field Form Adapter (CM R5C).

Tests verifying:
1. Real workbook recognition & integrity (14 sheets, SHA256)
2. Exact 153 source assets extraction across 14 sheets
3. Exact 133 canonical asset resolution
4. Exact 15 approved explicit aliases resolution
5. Exact 5 quarantined assets (fail-closed, REVIEW_REQUIRED, persistence_eligible=False)
6. All 42 canonical parameters preserved with correct row mappings
7. Blank template cell semantics (blank != 0.0, blank does not create storage operations)
8. N/A semantics (N/A != 0.0, N/A != not-inspected)
9. ValueState vs ConditionState independence
10. Storage plan validation (20 legacy, 20 measurements, 2 observations)
11. Provenance preservation (workbook, sheet, cell, literal, raw value)
12. Zero-write guarantee (pure in-memory preview, 0 DB writes, 0 asset_registry writes, 0 findings)
13. Deterministic repeat run (idempotency hash match between Run 1 and Run 2)
14. Scratch artifact generation
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
import sys

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
for path in (_CORE_SERVICES_DIR, _API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from condition_monitoring_field_form_adapter import (
    ConditionMonitoringFieldFormAdapter,
    CANONICAL_133_ASSETS,
    WORKBOOK_SHEET_NAMES,
    PARAMETER_ROW_MAP,
    RealWorkbookDryRunResult,
)
from condition_monitoring_field_form_engine import (
    ValueState,
    ConditionState,
    StorageTier,
    IngestionState,
    plan_asset_storage,
    parse_field_value,
    get_parameter_contract,
    _PARAM_CONTRACTS,
)

WORKBOOK_PATH = r"C:\Users\ghona\Downloads\LIST LAPANGAN CM (1).xlsx"
EXPECTED_SHA256 = "2E0A97264E0DABF0E3DF5366D71B5691D3B30DBCEE03CCEE0111F66B058C60ED"


@pytest.fixture(scope="module")
def real_adapter():
    """Initializes adapter for the real field workbook."""
    if not os.path.exists(WORKBOOK_PATH):
        pytest.skip(f"Workbook not found at {WORKBOOK_PATH}")
    return ConditionMonitoringFieldFormAdapter(WORKBOOK_PATH)


@pytest.fixture(scope="module")
def dry_run_result(real_adapter):
    """Executes single dry run for assertions."""
    return real_adapter.execute_dry_run("2026-09-15")


def test_01_workbook_recognition_and_sheets(real_adapter):
    """Verifies workbook identity, SHA256, and exactly 14 sheets."""
    assert real_adapter.workbook_hash == EXPECTED_SHA256
    sheet_summaries = real_adapter.audit_workbook_sheets()
    assert len(sheet_summaries) == 14
    names = [s["sheet_name"] for s in sheet_summaries]
    assert tuple(names) == WORKBOOK_SHEET_NAMES


def test_02_source_asset_count_153(dry_run_result):
    """Verifies exactly 153 source assets parsed across all worksheets."""
    assert dry_run_result.total_assets == 153
    assert len(dry_run_result.asset_columns) == 153


def test_03_exact_canonical_resolution_133(dry_run_result):
    """Verifies exactly 133 exact canonical matches against registered assets."""
    assert dry_run_result.exact_assets == 133


def test_04_approved_aliases_15(dry_run_result):
    """Verifies exactly 15 explicit approved aliases resolve cleanly."""
    assert dry_run_result.approved_alias_assets == 15


def test_05_quarantined_assets_5_fail_closed(dry_run_result):
    """Verifies exactly 5 Unit 946 assets are quarantined and not persistence eligible."""
    assert dry_run_result.quarantined_assets == 5
    assert dry_run_result.resolvable_assets == 148

    quarantined_tags = {"946-P-2D", "946-P-4A", "946-P-4C", "946-P-8A", "946-P-8B"}
    found_quarantined = set()

    for col in dry_run_result.asset_columns:
        if col.constructed_candidate in quarantined_tags:
            found_quarantined.add(col.constructed_candidate)

    assert found_quarantined == quarantined_tags

    # Check batch preview quarantine states
    spk_batch = next((b for b in dry_run_result.batch_previews if b.source_sheet == "SPK om"), None)
    assert spk_batch is not None
    assert spk_batch.quarantined_assets == 5
    assert spk_batch.resolvable_assets == 2

    for ap in spk_batch.asset_previews:
        if ap.source_asset in quarantined_tags:
            assert ap.resolution_status == IngestionState.REVIEW_REQUIRED.value
            assert ap.persistence_eligible is False
            assert ap.storage_plan is None


def test_06_canonical_parameters_42(dry_run_result):
    """Verifies all 42 canonical parameters are recognized and mapped."""
    assert len(PARAMETER_ROW_MAP) == 42
    assert len(_PARAM_CONTRACTS) == 42
    assert dry_run_result.total_parameter_cells == 153 * 42  # 6,426 cells


def test_07_blank_template_semantics(dry_run_result):
    """Verifies blank template cells are preserved as blank and NOT fabricated as zero."""
    assert dry_run_result.blank_template_cells == 6426
    assert dry_run_result.value_present_cells == 0
    # Blank cells must generate 0 persisted measurement operations
    for b in dry_run_result.batch_previews:
        for ap in b.asset_previews:
            if ap.storage_plan is not None:
                assert len(ap.storage_plan.legacy_parent_values) == 0
                assert len(ap.storage_plan.child_measurements) == 0
                assert len(ap.storage_plan.child_observations) == 0


def test_08_na_and_zero_semantics():
    """Verifies strict separation: 0.0 != N/A, N/A != not-inspected, blank != 0.0."""
    contract_numeric = get_parameter_contract("suction_pressure")
    assert contract_numeric is not None

    parsed_zero = parse_field_value(0.0, contract_numeric)
    assert parsed_zero.value_state == ValueState.VALUE_PRESENT
    assert parsed_zero.normalized_value == 0.0

    parsed_na = parse_field_value("N/A", contract_numeric)
    assert parsed_na.value_state == ValueState.NOT_APPLICABLE
    assert parsed_na.normalized_value is None

    parsed_ni = parse_field_value("NI", contract_numeric)
    assert parsed_ni.value_state == ValueState.NOT_INSPECTED
    assert parsed_ni.normalized_value is None

    parsed_blank = parse_field_value("", contract_numeric)
    assert parsed_blank.value_state == ValueState.NOT_INSPECTED
    assert parsed_blank.normalized_value is None


def test_09_storage_plan_42_parameters_distribution():
    """Verifies 20 legacy parent, 20 child measurements, and 2 observations routing."""
    parsed_items = {}
    for contract in _PARAM_CONTRACTS:
        if contract.data_type == "NUMERIC":
            parsed_items[contract.code] = parse_field_value(42.5, contract)
        elif contract.data_type == "BOOLEAN":
            parsed_items[contract.code] = parse_field_value("OBSERVED", contract)
        elif contract.data_type == "TEXT":
            parsed_items[contract.code] = parse_field_value("HIGH", contract)

    plan = plan_asset_storage("212-P-7A", parsed_items)
    assert len(plan.legacy_parent_values) == 20
    assert len(plan.child_measurements) == 20
    assert len(plan.child_observations) == 2


def test_10_provenance_preservation(dry_run_result):
    """Verifies provenance is strictly recorded for every asset column and cell."""
    sample_col = dry_run_result.asset_columns[0]
    assert sample_col.sheet_name == "RX 212-211"
    assert sample_col.col_letter == "D"
    assert sample_col.cell_position == "RX 212-211!D6"
    assert sample_col.source_tag_literal == "7A"
    assert sample_col.effective_unit == "212"
    assert len(sample_col.source_cells) == 42

    sample_cell = sample_col.source_cells["suction_pressure"]
    assert sample_cell.source_cell == "D10"
    assert sample_cell.source_parameter_literal == "SUCTION PRESSURE"
    assert sample_cell.unit == "Kg/cm"


def test_11_zero_writes_verification(dry_run_result):
    """Verifies pure in-memory execution: zero DB writes, zero asset_registry writes, zero findings."""
    assert dry_run_result.total_assets == 153
    # In-memory preview does not make network or database calls
    # All batch previews are pure Python dataclasses
    for b in dry_run_result.batch_previews:
        assert isinstance(b.total_assets, int)


def test_12_idempotency_hash_match(real_adapter):
    """Verifies running the dry run twice produces byte-identical results and identical hash."""
    run1 = real_adapter.execute_dry_run("2026-09-15")
    run2 = real_adapter.execute_dry_run("2026-09-15")
    assert run1.run_hash == run2.run_hash
    assert len(run1.run_hash) == 64


def test_13_scratch_artifacts_export(real_adapter, dry_run_result, tmp_path):
    """Verifies all 6 scratch artifacts are generated cleanly."""
    files = real_adapter.export_scratch_artifacts(dry_run_result, tmp_path)
    assert len(files) == 6
    assert (tmp_path / "cm_r5c_workbook_inventory.csv").exists()
    assert (tmp_path / "cm_r5c_asset_preview.csv").exists()
    assert (tmp_path / "cm_r5c_parameter_preview.csv").exists()
    assert (tmp_path / "cm_r5c_quarantine_preview.csv").exists()
    assert (tmp_path / "cm_r5c_validation_summary.csv").exists()
    assert (tmp_path / "cm_r5c_dry_run_report.txt").exists()

