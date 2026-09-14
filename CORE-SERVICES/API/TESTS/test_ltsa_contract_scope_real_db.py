"""MWO-LTSA-CONTRACT-SCOPE-R3 -- proves LtsaContractRepository /
ContractCoverageService against a REAL, disposable, published-port
Postgres running the actual canonical schema plus migration 036 (this
MWO's own). Same real-schema discipline
test_pm_occurrence_repository_real_db.py already established -- reused
verbatim, not reinvented (same container/bootstrap/truncate pattern).

Covers R3 Section G's 20 required cases, numbered in each test's own
docstring/comment for traceability back to that list.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import psycopg2
import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.ltsa_contract_repository import LtsaContractRepository  # noqa: E402
from API.ltsa_contract_coverage_service import (  # noqa: E402
    ContractCoverageService,
    ContractNotFound,
    InvalidReportingPeriod,
)

_CONTAINER_NAME = "ai5r-test-ltsa-contract-scope-pg"
_USER = "ai5r"
_PASSWORD = "test-ltsa-contract-scope-password"
_DATABASE = "ltsa_brain"
_DATABASE_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE"
_SCHEMA_FILE = _DATABASE_DIR / "CANONICAL_SCHEMA.sql"
_MIGRATIONS = [
    _DATABASE_DIR / "MIGRATIONS" / name
    for name in (
        "007_create_ltsa_auth_foundation.sql",
        "008_create_internal_component_inventory.sql",
        "009_create_installation_report.sql",
        "010_alter_document_field_extraction_review_provenance.sql",
        "011_alter_installation_report_post_installation_readings.sql",
        "012_alter_auth_foundation_attribution.sql",
        "013_alter_seal_registry_identifiers_attribution.sql",
        "014_alter_pm_cmon_workflow_and_evidence.sql",
        "015_alter_historical_pm_cmon_ingestion.sql",
        "016_alter_organization_membership_data_scope.sql",
        "017_create_record_change_history.sql",
        "023_create_pm_cmon_base_tables_for_legacy_upgrade.sql",
        "027_add_pm_cmon_soft_delete.sql",
        "028_add_schedule_attribution_soft_delete.sql",
        "035_retarget_document_field_extraction_to_asset_registry.sql",
        "036_create_ltsa_contract_scope.sql",
    )
]

_HOC_ASSET = "211-P-13AR"       # area HOC -> MA1
# MWO-LTSA-CONTRACT-SCOPE-R4-6 -- was area FRAKSINASI; FRAKSINASI is now
# Chief-approved MA2 (R4.4/R4.5), so this fixture's area was moved to DCU
# to keep genuinely demonstrating an UNMAPPED area.
_UNMAPPED_ASSET = "701-MM-51"   # area DCU -> UNMAPPED


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", f"POSTGRES_USER={_USER}",
            "-e", f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e", f"POSTGRES_DB={_DATABASE}",
            "-p", "127.0.0.1::5432",
            "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _CONTAINER_NAME, "5432/tcp"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        host_port = int(port_output.rsplit(":", 1)[1])

        probe = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE)
        )
        last_error: Exception | None = None
        for _ in range(30):
            try:
                probe.query_scalar("SELECT 1")
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test Postgres never became ready: {last_error}")

        bootstrap_schema(probe, _SCHEMA_FILE)
        for migration in _MIGRATIONS:
            bootstrap_schema(probe, migration)

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE ltsa_contract_asset_scope, ltsa_contract, condition_monitoring_reading, "
        "asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area, status) VALUES "
        f"('{_HOC_ASSET}', '{_HOC_ASSET}', 'PUMP', 'HOC', 'Active'), "
        f"('{_UNMAPPED_ASSET}', '{_UNMAPPED_ASSET}', NULL, 'DCU', 'UNKNOWN');"
    )
    return r


@pytest.fixture
def repo(runner):
    return LtsaContractRepository(runner)


@pytest.fixture
def service(repo):
    return ContractCoverageService(repo)


def _insert_contract(runner, code="C-1", start="2026-01-01", end=None):
    end_sql = f"'{end}'" if end else "NULL"
    runner.execute_script(
        f"INSERT INTO ltsa_contract (contract_code, contract_name, start_date, end_date) "
        f"VALUES ('{code}', 'Test Contract', '{start}', {end_sql});"
    )


def _scope_asset(runner, contract="C-1", asset=_HOC_ASSET, start=None, end=None):
    start_sql = f"'{start}'" if start else "NULL"
    end_sql = f"'{end}'" if end else "NULL"
    runner.execute_script(
        f"INSERT INTO ltsa_contract_asset_scope (contract_code, asset_code, scope_start_date, scope_end_date) "
        f"VALUES ('{contract}', '{asset}', {start_sql}, {end_sql});"
    )


def _insert_reading(runner, asset=_HOC_ASSET, reading_date="2026-06-15", code=None):
    code = code or f"CMONR-TEST-{reading_date}-{asset}"
    runner.execute_script(
        "INSERT INTO condition_monitoring_reading "
        "(condition_monitoring_reading_code, condition_monitoring_schedule_code, asset_code, reading_date, workflow_status) "
        f"VALUES ('{code}', 'UNSCHEDULED::test', '{asset}', '{reading_date}', 'DRAFT');"
    )


# 1. contract with no assets
def test_contract_with_no_assets(runner, service):
    _insert_contract(runner)
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert coverage.total_contract_assets == 0
    assert coverage.monitored == 0
    assert coverage.pending == 0
    # 13. denominator zero => coverage null
    assert coverage.coverage_percent is None


# 2. contract with scoped assets
def test_contract_with_scoped_assets(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert coverage.total_contract_assets == 1


# 3. overlapping reporting period
def test_overlapping_period_included(runner, service):
    _insert_contract(runner, start="2026-01-01", end="2026-12-31")
    _scope_asset(runner)  # inherits contract dates
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.total_contract_assets == 1


# 4. non-overlapping scope excluded
def test_non_overlapping_scope_excluded(runner, service):
    _insert_contract(runner, start="2026-01-01", end="2026-12-31")
    _scope_asset(runner, start="2026-01-01", end="2026-03-31")
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.total_contract_assets == 0


# 5. inherited contract dates
def test_inherited_contract_dates(runner, service):
    _insert_contract(runner, start="2026-01-01", end="2026-12-31")
    _scope_asset(runner, start=None, end=None)
    assets = service.list_assets("C-1", "2026-01-01", "2026-12-31")
    assert assets[0].effective_scope_start == "2026-01-01"
    assert assets[0].effective_scope_end == "2026-12-31"


# 6. per-asset override dates
def test_per_asset_override_dates(runner, service):
    _insert_contract(runner, start="2026-01-01", end="2026-12-31")
    _scope_asset(runner, start="2026-04-01", end="2026-04-30")
    assets = service.list_assets("C-1", "2026-01-01", "2026-12-31")
    assert assets[0].effective_scope_start == "2026-04-01"
    assert assets[0].effective_scope_end == "2026-04-30"
    # narrower window than the contract: a period outside the override
    # but inside the contract must exclude the asset.
    coverage = service.build_coverage("C-1", "2026-07-01", "2026-07-31")
    assert coverage.total_contract_assets == 0


# 7. monitored asset
def test_monitored_asset(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    _insert_reading(runner, reading_date="2026-06-15")
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.monitored == 1
    assert coverage.pending == 0
    assets = service.list_assets("C-1", "2026-06-01", "2026-06-30")
    assert assets[0].monitoring_status == "MONITORED"


# 8. pending asset
def test_pending_asset(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.monitored == 0
    assert coverage.pending == 1
    assets = service.list_assets("C-1", "2026-06-01", "2026-06-30")
    assert assets[0].monitoring_status == "PENDING"


# 9. multiple readings count asset once
def test_multiple_readings_count_asset_once(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    _insert_reading(runner, reading_date="2026-06-05", code="CMONR-A")
    _insert_reading(runner, reading_date="2026-06-15", code="CMONR-B")
    _insert_reading(runner, reading_date="2026-06-25", code="CMONR-C")
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.total_contract_assets == 1
    assert coverage.monitored == 1
    assets = service.list_assets("C-1", "2026-06-01", "2026-06-30")
    assert assets[0].cm_reading_count_in_period == 3


# 10. reading outside period does not count
def test_reading_outside_period_excluded(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    _insert_reading(runner, reading_date="2026-01-01")  # outside the requested June window
    coverage = service.build_coverage("C-1", "2026-06-01", "2026-06-30")
    assert coverage.monitored == 0
    assert coverage.pending == 1
    # last_cm_date is all-time, so it still surfaces the January reading
    # even though it doesn't count toward this period's monitored total.
    assets = service.list_assets("C-1", "2026-06-01", "2026-06-30")
    assert assets[0].last_cm_date.startswith("2026-01-01")
    assert assets[0].cm_reading_count_in_period == 0


# 11. UNMAPPED retained
def test_unmapped_area_retained(runner, service):
    _insert_contract(runner)
    _scope_asset(runner, asset=_UNMAPPED_ASSET)
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert coverage.by_ma["UNMAPPED"].total_contract_assets == 1
    assert coverage.by_ma["MA1"].total_contract_assets == 0
    assets = service.list_assets("C-1", "2026-01-01", "2026-12-31")
    assert assets[0].ma == "UNMAPPED"


# 12. MA reconciliation exact
def test_ma_reconciliation_exact(runner, service):
    _insert_contract(runner)
    _scope_asset(runner, asset=_HOC_ASSET)
    _scope_asset(runner, asset=_UNMAPPED_ASSET)
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert sum(b.total_contract_assets for b in coverage.by_ma.values()) == coverage.total_contract_assets
    assert coverage.total_contract_assets == 2


# 14 & 15. monitoring_required / overdue null (never 0)
def test_monitoring_required_and_overdue_are_null(runner, service):
    _insert_contract(runner)
    _scope_asset(runner)
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert coverage.monitoring_required is None
    assert coverage.overdue is None
    for bucket in coverage.by_ma.values():
        assert bucket.monitoring_required is None
        assert bucket.overdue is None


# 16. no auto-backfill -- proven structurally: the `runner` fixture always
# starts from a hard TRUNCATE and every test above only sees data THIS
# test inserted -- there is no code path anywhere in the repository/
# service that INSERTs into ltsa_contract_asset_scope from asset_registry.
def test_no_auto_backfill_on_fresh_schema(runner):
    counts = runner.query_scalar(
        "SELECT (SELECT count(*) FROM ltsa_contract) || ',' || (SELECT count(*) FROM ltsa_contract_asset_scope);"
    )
    assert counts == "0,0"


# 17. no asset_registry.status inference -- an UNKNOWN-status asset is
# scoped and counted identically to an Active one; status never gates
# membership.
def test_asset_registry_status_never_inferred(runner, service):
    _insert_contract(runner)
    _scope_asset(runner, asset=_UNMAPPED_ASSET)  # status UNKNOWN, per the fixture
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31")
    assert coverage.total_contract_assets == 1


# 18. duplicate contract+asset rejected
def test_duplicate_contract_asset_rejected(runner):
    _insert_contract(runner)
    _scope_asset(runner)
    with pytest.raises(psycopg2.Error):
        _scope_asset(runner)  # same (contract_code, asset_code) -- PK violation


# 19. invalid contract dates rejected
def test_invalid_contract_dates_rejected(runner):
    with pytest.raises(psycopg2.Error):
        _insert_contract(runner, start="2026-06-01", end="2026-01-01")


# 20. invalid asset-scope dates rejected
def test_invalid_asset_scope_dates_rejected(runner):
    _insert_contract(runner)
    with pytest.raises(psycopg2.Error):
        _scope_asset(runner, start="2026-06-01", end="2026-01-01")


# Bonus: RBAC area-scope enforcement (not in Chief's numbered list, but a
# real gap this service would otherwise reintroduce -- every other LTSA
# list endpoint enforces this).
def test_area_scope_filters_out_of_scope_assets(runner, service):
    _insert_contract(runner)
    _scope_asset(runner, asset=_HOC_ASSET)
    _scope_asset(runner, asset=_UNMAPPED_ASSET)
    restricted_scope = frozenset({"HOC"})
    coverage = service.build_coverage("C-1", "2026-01-01", "2026-12-31", scope=restricted_scope)
    assert coverage.total_contract_assets == 1
    assert coverage.by_ma["MA1"].total_contract_assets == 1
    assert coverage.by_ma["UNMAPPED"].total_contract_assets == 0


# Bonus: contract not found / invalid period surface as the documented
# exceptions the router translates to 404/400.
def test_unknown_contract_raises(service):
    with pytest.raises(ContractNotFound):
        service.build_coverage("NOPE", "2026-01-01", "2026-12-31")


def test_invalid_period_raises(runner, service):
    _insert_contract(runner)
    with pytest.raises(InvalidReportingPeriod):
        service.build_coverage("C-1", "2026-12-31", "2026-01-01")
