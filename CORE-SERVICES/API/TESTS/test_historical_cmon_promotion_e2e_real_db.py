"""MWO-LTSA-ATOMIC-CMON-PROMOTION-001 -- real-Postgres proof that
promote_historical_cmon_atomic() is genuinely atomic, idempotent, and
concurrency-safe, exact CMON mirror of test_historical_pm_promotion_e2e_
real_db.py's own discipline (same disposable-container pattern as
test_pm_occurrence_repository_real_db.py) but proving the SINGLE-
candidate atomic method directly (promote_historical_pm_atomic()'s own
sibling had no dedicated real-DB test before this file -- only its BATCH
sibling did), since that is the exact method this MWO added.

Failure injection (cases B/C in this MWO's own Gate D): a temporary CHECK
constraint that forbids document_field_extraction_id='DFE-BLOCK-SAVE'
from ever reaching status='SAVED' forces the atomic statement's own
mark_saved CTE to fail AFTER its ins CTE has already inserted a real
condition_monitoring_reading row (CTEs within one WITH-chain execute
within the same single statement, ins before mark_saved) -- proving the
already-inserted row is rolled back too, not left dangling. This is
deliberately the SAME failure point for both "after INSERT, before
status update" and "during status update": a genuinely single-statement
design (no explicit BEGIN/COMMIT) makes those two phrasings describe the
identical, only possible partial-failure boundary -- there is no gap
between them to inject two DIFFERENT failures into.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
_BACKEND_API_DIR = _CORE_SERVICES_DIR / "BACKEND-API"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR, _BACKEND_API_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402
from API.historical_pm_cmon_promotion_service import (  # noqa: E402
    AlreadyPromotedError,
    PromotionError,
    promote_cmon_reading_candidate,
)

_CONTAINER_NAME = "ai5r-test-cmon-promotion-e2e-pg"
_USER = "ai5r"
_PASSWORD = "test-cmon-promotion-e2e-password"
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
        "029_add_condition_monitoring_schedule_lifecycle.sql",
        "035_retarget_document_field_extraction_to_asset_registry.sql",
    )
]

_ASSET_CODE = "211-P-13AR"
_ACTOR = "22222222-2222-2222-2222-222222222222"
_SCHEDULE_CODE = "UNSCHEDULED::HOC-CMON-E2E-2026"


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


def _make_runner(pg_port):
    return DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )


@pytest.fixture
def runner(pg_port):
    r = _make_runner(pg_port)
    r.execute_script(
        "TRUNCATE condition_monitoring_reading, condition_monitoring_schedule, document_field_extraction, "
        "record_change_history, asset_registry, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(f"INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) VALUES ('{_ASSET_CODE}', '{_ASSET_CODE}', 'PUMP', 'HOC');")
    r.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_ASSET_CODE}', 'HOC');")
    return r


def _insert_candidate(
    runner, candidate_id, *, status="REVIEWED", reading_date="2026-07-01",
    asset_code=_ASSET_CODE, fields_override=None,
):
    base_fields = {
        "reading_date": reading_date, "asset_type": "PUMP", "mechseal_temp_de": 58.0,
        "finding": "STANDBY, bocor dari draingland 1/2 detik",
    }
    if fields_override:
        base_fields.update(fields_override)
    fields = json.dumps(base_fields)
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status, pump_tag_number) VALUES "
        f"('{candidate_id}', 'PDF-E2E', 'PDF', 'HISTORICAL_CMON_READING_CANDIDATE', "
        f"'deterministic_workbook_table_parser', '{fields}'::jsonb, '{status}', '{asset_code}');"
    )


def _cmon_count(runner) -> int:
    return int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_reading") or "0")


def _candidate_status(runner, candidate_id) -> str | None:
    row = runner.query_scalar(
        f"SELECT status FROM document_field_extraction WHERE document_field_extraction_id = '{candidate_id}'"
    )
    return row


def test_a_normal_promotion_creates_final_record_once_and_transitions_candidate_once(runner):
    _insert_candidate(runner, "DFE-A")
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    record = promote_cmon_reading_candidate(
        "DFE-A", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert record["asset_code"] == _ASSET_CODE
    assert record["finding"] == "STANDBY, bocor dari draingland 1/2 detik"
    assert _cmon_count(runner) == 1
    assert _candidate_status(runner, "DFE-A") == "SAVED"


def test_b_and_c_failure_after_insert_before_status_update_rolls_back_both(runner):
    # Failure injection: forbid THIS specific candidate id from ever
    # reaching status='SAVED' -- forces the atomic statement's mark_saved
    # CTE to fail after its ins CTE already produced a real row.
    _insert_candidate(runner, "DFE-BLOCK-SAVE")
    runner.execute_script(
        "ALTER TABLE document_field_extraction ADD CONSTRAINT test_block_save "
        "CHECK (document_field_extraction_id <> 'DFE-BLOCK-SAVE' OR status <> 'SAVED');"
    )
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    with pytest.raises(Exception):  # noqa: B017 -- real Postgres constraint-violation exception, not a Fake
        promote_cmon_reading_candidate(
            "DFE-BLOCK-SAVE", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )

    # The ins CTE's INSERT genuinely ran (it precedes mark_saved in the
    # WITH-chain) -- but the whole single statement rolled back when
    # mark_saved's own UPDATE hit the CHECK constraint. Proof: zero rows
    # in the final table, candidate untouched.
    assert _cmon_count(runner) == 0
    assert _candidate_status(runner, "DFE-BLOCK-SAVE") == "REVIEWED"

    runner.execute_script("ALTER TABLE document_field_extraction DROP CONSTRAINT test_block_save;")


def test_d_retry_after_injected_failure_produces_exactly_one_final_record(runner):
    _insert_candidate(runner, "DFE-RETRY")
    runner.execute_script(
        "ALTER TABLE document_field_extraction ADD CONSTRAINT test_block_save "
        "CHECK (document_field_extraction_id <> 'DFE-RETRY' OR status <> 'SAVED');"
    )
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    with pytest.raises(Exception, match="test_block_save"):
        promote_cmon_reading_candidate(
            "DFE-RETRY", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )
    assert _cmon_count(runner) == 0
    assert _candidate_status(runner, "DFE-RETRY") == "REVIEWED"

    runner.execute_script("ALTER TABLE document_field_extraction DROP CONSTRAINT test_block_save;")

    promote_cmon_reading_candidate(
        "DFE-RETRY", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert _cmon_count(runner) == 1
    assert _candidate_status(runner, "DFE-RETRY") == "SAVED"

    with pytest.raises(AlreadyPromotedError):
        promote_cmon_reading_candidate(
            "DFE-RETRY", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )
    assert _cmon_count(runner) == 1


def test_e_repeated_promotion_request_no_duplicate(runner):
    _insert_candidate(runner, "DFE-E")
    cmon_repo = ConditionMonitoringReadingRepository(runner)
    promote_cmon_reading_candidate(
        "DFE-E", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    for _ in range(3):
        with pytest.raises(AlreadyPromotedError):
            promote_cmon_reading_candidate(
                "DFE-E", cmon_repository=cmon_repo,
                condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
            )
    assert _cmon_count(runner) == 1


def test_f_concurrent_double_attempt_no_duplicate_final_record(pg_port, runner):
    # Real concurrency, real FOR UPDATE row lock, two real connections --
    # not simulated. Both threads race to promote the SAME candidate_id;
    # the atomic statement's own `FOR UPDATE` on the candidate row
    # serializes them, so the second to actually commit must observe the
    # first's already-SAVED state and become a safe no-op (raising
    # AlreadyPromotedError, never a second insert).
    _insert_candidate(runner, "DFE-F")
    results: list[tuple[str, Exception | None]] = []
    lock = threading.Lock()

    def _attempt():
        conn_runner = _make_runner(pg_port)
        repo = ConditionMonitoringReadingRepository(conn_runner)
        try:
            promote_cmon_reading_candidate(
                "DFE-F", cmon_repository=repo,
                condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
            )
            with lock:
                results.append(("OK", None))
        except AlreadyPromotedError as error:
            with lock:
                results.append(("ALREADY_PROMOTED", error))
        except Exception as error:  # noqa: BLE001
            with lock:
                results.append(("ERROR", error))

    threads = [threading.Thread(target=_attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    outcomes = [r[0] for r in results]
    assert outcomes.count("OK") == 1, f"expected exactly one real promotion, got {outcomes}"
    assert outcomes.count("ALREADY_PROMOTED") == 1, f"expected exactly one safe no-op, got {outcomes}"
    verify_runner = _make_runner(pg_port)
    assert _cmon_count(verify_runner) == 1


@pytest.mark.parametrize("iteration", range(20))
def test_concurrent_waiter_confirms_committed_canonical_record(runner, iteration):
    candidate_id = f"DFE-WAIT-{iteration}"
    _insert_candidate(runner, candidate_id)
    first = runner._direct_connect()
    second = runner._direct_connect()
    first.autocommit = False
    results = []
    snapshots = []

    class ConnectionRunner:
        def __init__(self, connection):
            self.connection = connection

        def query_scalar(self, sql):
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                value = str(cursor.fetchone()[0])
            if self.connection is second and "WITH cand AS" in sql:
                snapshots.append(json.loads(value))
            return value

    def promote(connection):
        return promote_cmon_reading_candidate(
            candidate_id, cmon_repository=ConditionMonitoringReadingRepository(ConnectionRunner(connection)),
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )

    def attempt():
        try:
            promote(second)
            results.append("OK")
        except AlreadyPromotedError:
            results.append("ALREADY_PROMOTED")
        except Exception as error:
            results.append(error)

    thread = threading.Thread(target=attempt)
    try:
        promote(first)
        thread.start()
        # Release the winner only after PostgreSQL reports the waiter's
        # lock dependency, ensuring its statement snapshot predates commit.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            blocked = runner.query_scalar(
                f"SELECT {first.get_backend_pid()} = ANY(pg_blocking_pids({second.get_backend_pid()}))"
            )
            if blocked == "True":
                break
        else:
            pytest.fail("second promotion did not wait on the first transaction")
        first.commit()
        results.append("OK")
        thread.join(timeout=10)
        assert not thread.is_alive()
        assert sorted(results, key=str) == ["ALREADY_PROMOTED", "OK"], results
        assert snapshots[0]["candidate_status"] == "SAVED"
        assert snapshots[0]["already"] is None
        assert snapshots[0]["inserted"] is None
        assert second.get_transaction_status() == 0
        assert _cmon_count(runner) == 1
        assert _candidate_status(runner, candidate_id) == "SAVED"
    finally:
        first.rollback()
        if thread.ident is not None:
            thread.join(timeout=10)
        first.close()
        second.close()


def test_g_pm_promotion_behavior_is_untouched_by_this_change(runner):
    # This MWO's own scope boundary, proven, not just asserted: PM's own
    # promote_historical_pm_atomic() code path was not modified at all --
    # its dedicated e2e coverage lives in
    # test_historical_pm_promotion_e2e_real_db.py and is unaffected by
    # anything in this file. This test only proves that inserting a PM
    # candidate through the SAME schema/fixtures this file uses does not
    # cross-contaminate condition_monitoring_reading -- a CMON-side
    # regression guard, not a re-proof of PM's own atomicity (already
    # covered elsewhere).
    fields = json.dumps({"occurrence_date": "2026-07-02", "asset_type": "PUMP"})
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status, pump_tag_number) VALUES "
        f"('DFE-PM-CROSS-CHECK', 'PDF-E2E', 'PDF', 'HISTORICAL_PM_OCCURRENCE_CANDIDATE', "
        f"'deterministic_workbook_table_parser', '{fields}'::jsonb, 'REVIEWED', '{_ASSET_CODE}');"
    )
    from API.pm_occurrence_repository import PMOccurrenceRepository
    pm_repo = PMOccurrenceRepository(runner)
    pm_repo.promote_historical_pm_atomic(
        "DFE-PM-CROSS-CHECK", pm_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert _cmon_count(runner) == 0  # the PM promotion never touched condition_monitoring_reading


def test_h_cmon_promotion_produces_a_well_formed_final_record(runner):
    _insert_candidate(runner, "DFE-H")
    cmon_repo = ConditionMonitoringReadingRepository(runner)
    record = promote_cmon_reading_candidate(
        "DFE-H", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert record["condition_monitoring_reading_code"].startswith("CMONR-")
    assert record["asset_code"] == _ASSET_CODE
    assert record["asset_type"] == "PUMP"
    assert str(record["reading_date"]).startswith("2026-07-01")
    assert float(record["mechseal_temp_de"]) == 58.0
    assert record["provenance"] == "HISTORICAL_IMPORT"
    assert record["source_reference"] == "document_field_extraction:DFE-H"


def test_canonical_create_failure_precondition_not_met(runner):
    # Case 2 of Gate 4: canonical create failure.
    # A candidate whose asset is NOT in asset_registry cannot be inserted.
    # Proves all-or-nothing: statement rolls back, 0 rows inserted, candidate remains REVIEWED.
    runner.execute_script(
        "INSERT INTO document_field_extraction "
        "(document_field_extraction_id, source_document_id, source_document_type, detected_document_type, "
        "extraction_provider, extracted_fields, status, pump_tag_number) VALUES "
        "('DFE-BAD-ASSET', 'PDF-E2E', 'PDF', 'HISTORICAL_CMON_READING_CANDIDATE', "
        "'deterministic_workbook_table_parser', '{\"reading_date\": \"2026-07-01\"}'::jsonb, 'REVIEWED', NULL);"
    )
    cmon_repo = ConditionMonitoringReadingRepository(runner)
    with pytest.raises(PromotionError, match="not eligible"):
        promote_cmon_reading_candidate(
            "DFE-BAD-ASSET", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )
    assert _cmon_count(runner) == 0
    assert _candidate_status(runner, "DFE-BAD-ASSET") == "REVIEWED"


def test_conflict_with_different_candidate_same_asset_and_date_raises(runner):
    # Case 7 of Gate 4: conflict check.
    # Two DIFFERENT candidates with the exact same (asset_code, reading_date).
    # The first promotes successfully; the second must be rejected with conflict,
    # leaving exactly 1 record in condition_monitoring_reading and the second candidate REVIEWED.
    _insert_candidate(runner, "DFE-FIRST", reading_date="2026-07-10")
    _insert_candidate(runner, "DFE-SECOND", reading_date="2026-07-10")
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    first_record = promote_cmon_reading_candidate(
        "DFE-FIRST", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert first_record["condition_monitoring_reading_code"].startswith("CMONR-")
    assert _cmon_count(runner) == 1
    assert _candidate_status(runner, "DFE-FIRST") == "SAVED"

    with pytest.raises(PromotionError, match="conflicts with existing condition_monitoring_reading"):
        promote_cmon_reading_candidate(
            "DFE-SECOND", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
        )
    assert _cmon_count(runner) == 1
    assert _candidate_status(runner, "DFE-SECOND") == "REVIEWED"


@pytest.mark.parametrize("asset_code,asset_type", [
    ("701-MM-51", None), ("702-MM-51", None),
    ("101-LRC-102", "LIQUID RING COMPRESSOR"),
    ("211-P-25A", "PUMP"), ("211-P-25B", "PUMP"),
    ("P-201A-DMI", "PUMP"), ("P-201B-DMI", "PUMP"),
])
def test_representative_registry_only_asset(runner, asset_code, asset_type):
    type_sql = "NULL" if asset_type is None else f"'{asset_type}'"
    runner.execute_script(
        "INSERT INTO asset_registry (asset_code, asset_name, asset_type) "
        f"VALUES ('{asset_code}', '{asset_code}', {type_sql});"
    )
    assert runner.query_scalar(f"SELECT count(*) FROM ltsa_pumps WHERE tag_number = '{asset_code}'") == "0"
    _insert_candidate(runner, "DFE-REGISTRY", asset_code=asset_code)
    record = promote_cmon_reading_candidate(
        "DFE-REGISTRY", cmon_repository=ConditionMonitoringReadingRepository(runner),
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert record["asset_code"] == asset_code
    assert record["asset_type"] == asset_type
    assert _cmon_count(runner) == 1
    assert _candidate_status(runner, "DFE-REGISTRY") == "SAVED"


def test_non_pump_ltsa_assets_promote_without_fabricated_type(runner):
    # Case 8 of Gate 4 + Gate 2 regression test:
    # 701-MM-51 (asset_type=NULL) and 101-LRC-102 (asset_type='LIQUID RING COMPRESSOR')
    # live in asset_registry only (never in ltsa_pumps).
    # Both must promote legitimately without requiring asset_type=PUMP or fabricating asset types.
    runner.execute_script(
        "INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) "
        "VALUES ('701-MM-51', '701-MM-51', NULL, 'HOC'), "
        "       ('101-LRC-102', '101-LRC-102', 'LIQUID RING COMPRESSOR', 'HOC');"
    )
    _insert_candidate(runner, "DFE-MOTOR", asset_code="701-MM-51", reading_date="2026-07-15")
    _insert_candidate(runner, "DFE-COMP", asset_code="101-LRC-102", reading_date="2026-07-16")
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    motor_record = promote_cmon_reading_candidate(
        "DFE-MOTOR", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert motor_record["asset_code"] == "701-MM-51"
    assert motor_record["asset_type"] is None  # Never fabricated as 'PUMP'
    assert _candidate_status(runner, "DFE-MOTOR") == "SAVED"

    comp_record = promote_cmon_reading_candidate(
        "DFE-COMP", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert comp_record["asset_code"] == "101-LRC-102"
    assert comp_record["asset_type"] == "LIQUID RING COMPRESSOR"
    assert _candidate_status(runner, "DFE-COMP") == "SAVED"


@pytest.mark.parametrize("raw_tag,canonical_tag", [
    ("DMI-P-201A", "P-201A-DMI"), ("DMI-P-201B", "P-201B-DMI"),
])
def test_alias_resolved_asset_promotes_with_canonical_identity(runner, raw_tag, canonical_tag):
    # Case 9 of Gate 4:
    # Curated alias DMI-P-201A -> P-201A-DMI resolves to canonical asset P-201A-DMI.
    # Staging sets pump_tag_number to the matched canonical tag 'P-201A-DMI'.
    # Promotion creates canonical condition_monitoring_reading with asset_code 'P-201A-DMI'.
    runner.execute_script(
        "INSERT INTO asset_registry (asset_code, asset_name, asset_type, area) "
        f"VALUES ('{canonical_tag}', 'SLOP OIL PUMP', 'PUMP', 'DMI');"
    )
    from historical_pm_cmon_extraction import match_pump_tag
    match = match_pump_tag(raw_tag, {canonical_tag})
    assert match.outcome == "EXACT_MATCH"
    assert match.matched_tag == canonical_tag
    _insert_candidate(runner, "DFE-ALIAS", asset_code=match.matched_tag, reading_date="2026-07-20")
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    record = promote_cmon_reading_candidate(
        "DFE-ALIAS", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code=_SCHEDULE_CODE, promoted_by=_ACTOR,
    )
    assert record["asset_code"] == canonical_tag
    assert record["asset_type"] == "PUMP"
    assert _candidate_status(runner, "DFE-ALIAS") == "SAVED"


def test_unscheduled_historical_cmon_does_not_require_schedule_row_and_scheduled_does(runner):
    # Case 10 of Gate 4 + Gate 3 regression test:
    # 1. Historical UNSCHEDULED:: CMON must NOT require a real condition_monitoring_schedule row.
    # Proof: condition_monitoring_schedule has 0 rows. Promotion with UNSCHEDULED:: succeeds.
    assert int(runner.query_scalar("SELECT count(*) FROM condition_monitoring_schedule") or "0") == 0
    _insert_candidate(runner, "DFE-UNSCHED", reading_date="2026-07-22")
    cmon_repo = ConditionMonitoringReadingRepository(runner)

    rec = promote_cmon_reading_candidate(
        "DFE-UNSCHED", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code="UNSCHEDULED::HOC-CMON-APRIL-2026", promoted_by=_ACTOR,
    )
    assert rec["condition_monitoring_schedule_code"] == "UNSCHEDULED::HOC-CMON-APRIL-2026"
    assert _candidate_status(runner, "DFE-UNSCHED") == "SAVED"

    # 2. Genuinely scheduled CMON MUST retain schedule validation.
    # Attempting to promote with a real schedule code when that schedule row does NOT exist must fail.
    _insert_candidate(runner, "DFE-SCHED", reading_date="2026-07-25")
    with pytest.raises(PromotionError, match="precondition"):
        promote_cmon_reading_candidate(
            "DFE-SCHED", cmon_repository=cmon_repo,
            condition_monitoring_schedule_code="CMS-REAL-SCHEDULE-1", promoted_by=_ACTOR,
        )
    assert _candidate_status(runner, "DFE-SCHED") == "REVIEWED"

    # 3. Once the schedule row genuinely exists, promotion succeeds.
    runner.execute_script(
        f"INSERT INTO condition_monitoring_schedule (condition_monitoring_schedule_code, asset_code, asset_type) "
        f"VALUES ('CMS-REAL-SCHEDULE-1', '{_ASSET_CODE}', 'PUMP');"
    )
    sched_rec = promote_cmon_reading_candidate(
        "DFE-SCHED", cmon_repository=cmon_repo,
        condition_monitoring_schedule_code="CMS-REAL-SCHEDULE-1", promoted_by=_ACTOR,
    )
    assert sched_rec["condition_monitoring_schedule_code"] == "CMS-REAL-SCHEDULE-1"
    assert _candidate_status(runner, "DFE-SCHED") == "SAVED"
