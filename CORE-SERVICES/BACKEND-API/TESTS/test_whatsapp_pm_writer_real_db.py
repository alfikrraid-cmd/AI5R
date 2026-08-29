"""MWO: AUTHORITATIVE WHATSAPP PM CANONICAL PERSISTENCE -- proves the new
WhatsApp PM writer (_confirm_pm in whatsapp_intake_service.py, calling
PMOccurrenceRepository.create_draft/create_ad_hoc_draft) against a REAL,
disposable, published-port Postgres running the actual canonical schema --
the same real-schema discipline test_whatsapp_cmon_writer_real_db.py's own
header already established, adapted for PM's own domain semantics
(51667f9's repository support), never assuming CMON's shape.

Only the PM writer is backed by real Postgres here -- FakeIntakeRepository
(already proven correct by the Fake WhatsApp test suite) still owns the
pending-row state machine, driven through the real FastAPI webhook route
exactly as production does.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_BACKEND_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _BACKEND_API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_BACKEND_API_DIR, _CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.pm_occurrence_repository import PMOccurrenceRepository  # noqa: E402
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402

from TESTS.test_whatsapp_webhook_router import (  # noqa: E402
    FakeIntakeRepository,
    FakeOutboundClient,
    SENDER_A,
    SENDER_B,
    _identity,
    _message_envelope,
    _post,
    _wire,
)

_CONTAINER_NAME = "ai5r-test-whatsapp-pm-writer-pg"
_USER = "ai5r"
_PASSWORD = "test-whatsapp-pm-writer-password"
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
    )
]

_ASSET_CODE = "211-P-13AR"
_PRODUCTION_PM_TEXT = "PM 211-P-13AR ganti oli mesin"
_ACTOR = "11111111-1111-1111-1111-111111111111"


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
        "TRUNCATE pm_occurrence, pm_schedule, condition_monitoring_reading, condition_monitoring_schedule, "
        "record_change_history, ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    r.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_ASSET_CODE}', 'HOC');")
    return r


@pytest.fixture
def pm_repo(runner):
    return PMOccurrenceRepository(runner)


def _expected_today() -> str:
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()


def test_pm_real_db_three_message_flow_writes_exactly_one_canonical_record(monkeypatch, pm_repo, runner):
    # Scenarios 1, 2, 6, 7, 12, 13 -- the exact 3-message production-shaped
    # flow: missing occurrence_date resolved via the state-machine
    # boundary (zero canonical writes on the date-only "Ya"), then a
    # genuinely separate final "Ya" performs the real canonical INSERT
    # against real Postgres. Zero open schedules -> ad-hoc, no fake
    # pm_schedule row, correct audit trail, duplicate-confirmation and
    # lowercase-explicit-code idempotency both proven against the real DB.
    expected_today = _expected_today()
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    # Message 1: missing date.
    _post(_message_envelope(message_id="wamid.pmrealA", text=_PRODUCTION_PM_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"
    assert outbound.calls[-1] == (SENDER_A, "Tanggal PM belum ada. Gunakan hari ini?")

    # Message 2: answers the date question only -- zero canonical writes.
    _post(_message_envelope(message_id="wamid.pmrealB", text="Ya"))
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert pm_repo.find_by_source_reference(f"WHATSAPP::{repo.rows[0]['intake_id']}") is None
    schedule_count = runner.query_scalar("SELECT count(*) FROM pm_schedule")
    assert schedule_count == "0"  # zero open schedules -- no fake row created here either

    # Message 3: final confirmation -- real canonical INSERT.
    response = _post(_message_envelope(message_id="wamid.pmrealC", text="Ya"))
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"

    intake_id = repo.rows[0]["intake_id"]
    record = pm_repo.find_by_source_reference(f"WHATSAPP::{intake_id}")
    assert record is not None
    assert record["asset_code"] == _ASSET_CODE
    assert record["asset_type"] == "PUMP"
    assert record["occurrence_date"].startswith(expected_today)
    assert record["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"
    assert record["provenance"] == "WHATSAPP"
    assert record["source_reference"] == f"WHATSAPP::{intake_id}"

    # No fake pm_schedule row (Scenario 13).
    assert runner.query_scalar("SELECT count(*) FROM pm_schedule") == "0"

    # Audit/history correct (Scenario 12): CREATE audit only, no
    # PM_SCHEDULE event (nothing real to complete).
    import json
    audit_rows = json.loads(
        runner.query_scalar(
            "SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM "
            "(SELECT entity_type, entity_id, reason FROM record_change_history) t;"
        )
    )
    assert len(audit_rows) == 1
    assert audit_rows[0] == {"entity_type": "PM_OCCURRENCE", "entity_id": record["pm_occurrence_code"], "reason": "CREATE"}

    reply = outbound.calls[-1][1]
    assert "berhasil disimpan" in reply
    assert f"Tanggal: {expected_today}" in reply
    assert f"Kode: {record['pm_occurrence_code']}" in reply
    assert "Ad-hoc" in reply

    # Scenario 6: duplicate confirmation (plain "Ya") -- idempotent, count
    # stays 1.
    repeat = _post(_message_envelope(message_id="wamid.pmrealD", text="Ya"))
    assert repeat.status_code == 200
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1

    # Explicit-code retry, uppercase.
    code = repo.rows[0]["confirmation_id"]
    canonical_code = record["pm_occurrence_code"]
    explicit_retry = _post(_message_envelope(message_id="wamid.pmrealE", text=f"YA {code}"))
    assert explicit_retry.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, f"PM {_ASSET_CODE} sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1

    # Scenario 7: lowercase explicit WA-CONF code -- same case-
    # insensitivity fix (f76fcbb) PM inherits from the shared confirmation
    # parser.
    lowercase_retry = _post(_message_envelope(message_id="wamid.pmrealF", text=f"YA {code.lower()}"))
    assert lowercase_retry.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, f"PM {_ASSET_CODE} sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1


def test_pm_real_db_one_open_schedule_used_and_auto_completed(monkeypatch, pm_repo, runner):
    # Scenario 3: exactly one open schedule -> real schedule used, then
    # auto-completed by create_draft's existing (repaired) semantics.
    runner.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('PMSCHED-REAL-1', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'ACTIVE');"
    )
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmonerealA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmonerealB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmonerealC", text="Ya"))

    intake_id = repo.rows[0]["intake_id"]
    record = pm_repo.find_by_source_reference(f"WHATSAPP::{intake_id}")
    assert record is not None
    assert record["pm_schedule_code"] == "PMSCHED-REAL-1"

    schedule_status = runner.query_scalar("SELECT status FROM pm_schedule WHERE pm_schedule_code = 'PMSCHED-REAL-1'")
    assert schedule_status == "COMPLETED"

    reply = outbound.calls[-1][1]
    assert "Jadwal: PMSCHED-REAL-1" in reply


def test_pm_real_db_multiple_open_schedules_clarification_no_write(monkeypatch, pm_repo, runner):
    # Scenario 4: multiple open schedules -> deterministic clarification,
    # zero canonical writes.
    runner.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('PMSCHED-A', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'ACTIVE'), "
        f"('PMSCHED-B', '{_ASSET_CODE}', 'PUMP', 'Inspection', 'Weekly', 'TIME_BASED', 'PLANNED');"
    )
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmmultirealA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmmultirealB", text="Ya"))
    response = _post(_message_envelope(message_id="wamid.pmmultirealC", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    occurrence_count = runner.query_scalar("SELECT count(*) FROM pm_occurrence")
    assert occurrence_count == "0"
    reply = outbound.calls[-1][1]
    assert "Ditemukan lebih dari satu jadwal PM" in reply
    assert "Lubrication" in reply and "Inspection" in reply


def test_pm_real_db_terminal_only_schedules_uses_unscheduled_sentinel(monkeypatch, pm_repo, runner):
    # Scenario 5: terminal-only schedules (CANCELLED/COMPLETED) treated as
    # zero-open -> ad-hoc write, consistent with 51667f9.
    runner.execute_script(
        f"INSERT INTO pm_schedule (pm_schedule_code, asset_code, asset_type, procedure, frequency, trigger_type, status) "
        f"VALUES ('PMSCHED-DONE', '{_ASSET_CODE}', 'PUMP', 'Lubrication', 'Monthly', 'TIME_BASED', 'COMPLETED'), "
        f"('PMSCHED-CANCEL', '{_ASSET_CODE}', 'PUMP', 'Inspection', 'Weekly', 'TIME_BASED', 'CANCELLED');"
    )
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmtermrealA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmtermrealB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmtermrealC", text="Ya"))

    intake_id = repo.rows[0]["intake_id"]
    record = pm_repo.find_by_source_reference(f"WHATSAPP::{intake_id}")
    assert record is not None
    assert record["pm_schedule_code"] == "UNSCHEDULED::WHATSAPP"


def test_pm_real_db_wrong_sender_cannot_confirm(monkeypatch, pm_repo, runner):
    # Scenario 8.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="user-a"), SENDER_B: _identity(user_id="user-b")})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmsenderA", sender="15550000001", text=_PRODUCTION_PM_TEXT))
    response = _post(_message_envelope(message_id="wamid.pmsenderB", sender="15550000002", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    assert runner.query_scalar("SELECT count(*) FROM pm_occurrence") == "0"


def test_pm_real_db_wrong_org_cannot_confirm(monkeypatch, pm_repo, runner):
    # Scenario 9.
    repo = FakeIntakeRepository({SENDER_A: _identity(organization_id="org-tap", user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmorgA", text=_PRODUCTION_PM_TEXT))
    repo.rows[0]["organization_id"] = "org-other"

    response = _post(_message_envelope(message_id="wamid.pmorgB", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    assert runner.query_scalar("SELECT count(*) FROM pm_occurrence") == "0"


def test_pm_real_db_nonexistent_pump_rejected_zero_writes(monkeypatch, pm_repo, runner):
    # Scenario 10.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmnopumpA", text="PM 999-P-99 ganti oli"))
    assert "UNKNOWN_PUMP" in repo.rows[0]["validation_result"]["errors"]

    response = _post(_message_envelope(message_id="wamid.pmnopumpB", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] != "CONFIRMED"
    assert runner.query_scalar("SELECT count(*) FROM pm_occurrence") == "0"


def test_pm_real_db_recovery_after_write_success_transition_failure(monkeypatch, pm_repo, runner):
    # Scenario 11: canonical write succeeded on a prior attempt but the
    # intake's own CONFIRMED transition never completed (simulated crash
    # between the two). Retrying must recover via source_reference,
    # complete the intake transition, and never write a second canonical
    # record.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmrecoverA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmrecoverB", text="Ya"))
    intake_id = repo.rows[0]["intake_id"]
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"

    # Simulate the prior successful write directly against the real DB,
    # via the real ad-hoc write path (zero open schedules).
    prior = pm_repo.create_ad_hoc_draft(
        asset_code=_ASSET_CODE, asset_type="PUMP", occurrence_date=_expected_today(),
        activities=None, remarks=None, created_by=_ACTOR,
        source_reference=f"WHATSAPP::{intake_id}", provenance="WHATSAPP",
    )
    assert prior is not None

    response = _post(_message_envelope(message_id="wamid.pmrecoverC", text="Ya"))

    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"
    assert len(pm_repo.list_by_asset(_ASSET_CODE)) == 1  # still exactly the one pre-existing record
    reply = outbound.calls[-1][1]
    assert reply != "Gagal menyimpan PM. Silakan coba lagi."


def test_pm_real_db_never_creates_cmon_records(monkeypatch, pm_repo, runner):
    # No CMON mutation from the PM writer.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id=_ACTOR)})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, pm_repository=pm_repo)

    _post(_message_envelope(message_id="wamid.pmnocmonA", text=_PRODUCTION_PM_TEXT))
    _post(_message_envelope(message_id="wamid.pmnocmonB", text="Ya"))
    _post(_message_envelope(message_id="wamid.pmnocmonC", text="Ya"))

    cmon_repo = ConditionMonitoringReadingRepository(runner)
    assert cmon_repo.list_by_asset(_ASSET_CODE) == []
