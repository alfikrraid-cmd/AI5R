"""PRODUCTION E2E PHASE 2 -- proves the authoritative WhatsApp CMON writer
(condition_monitoring_reading_repository.py's create_draft/
create_ad_hoc_draft) against a REAL, disposable, published-port Postgres
running the actual canonical schema -- the same real-schema discipline
PRODUCTS/LTSA-BRAIN/INGESTION/TEST/test_installation_fitment_migration.py's
own header already established.

This is the regression the prior Fake-repository-only WhatsApp test suite
(test_whatsapp_webhook_router.py) could never catch: a real SQL syntax
error (SQLSTATE 42601, stray "VALUES" before an INSERT...SELECT, plus a
misplaced RETURNING clause) that fails on every single call regardless of
payload, but is invisible to any test that only exercises
FakeConditionMonitoringReadingRepository.

Only the CMON writer is backed by real Postgres here -- FakeIntakeRepository
(already proven correct by the 109-test Fake suite) still owns the pending-
row state machine, driven through the real FastAPI webhook route exactly as
production does.
"""

from __future__ import annotations

import subprocess
import sys
import time
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
from API.condition_monitoring_reading_repository import ConditionMonitoringReadingRepository  # noqa: E402

from TESTS.test_whatsapp_webhook_router import (  # noqa: E402
    FakeIntakeRepository,
    FakeOutboundClient,
    SENDER_A,
    _identity,
    _message_envelope,
    _post,
    _wire,
)

_CONTAINER_NAME = "ai5r-test-whatsapp-cmon-writer-pg"
_USER = "ai5r"
_PASSWORD = "test-whatsapp-cmon-writer-password"
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
    )
]

_ASSET_CODE = "211-P-13AR"
_PRODUCTION_CMON_TEXT = "CMON 211-P-13AR: ditemukan kebocoran mechanical seal"


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
def cmon_repo(pg_port):
    runner = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    runner.execute_script(
        "TRUNCATE condition_monitoring_reading, condition_monitoring_schedule, record_change_history, "
        "ltsa_pumps RESTART IDENTITY CASCADE;"
    )
    runner.execute_script(f"INSERT INTO ltsa_pumps (tag_number, area) VALUES ('{_ASSET_CODE}', 'HOC');")
    return ConditionMonitoringReadingRepository(runner)


def test_real_db_three_message_flow_writes_exactly_one_canonical_record(monkeypatch, cmon_repo):
    # REAL_DB_REGRESSION -- the exact 3-message production flow, this time
    # with the CMON writer backed by real Postgres running the actual
    # canonical schema, proving both the state-machine ordering fix
    # (fee571a) and the SQL syntax fix land correctly together.
    repo = FakeIntakeRepository({SENDER_A: _identity(user_id="11111111-1111-1111-1111-111111111111")})
    outbound = FakeOutboundClient()
    _wire(monkeypatch, repo, outbound, cmon_repository=cmon_repo)

    # Message 1.
    _post(_message_envelope(message_id="wamid.realdbA", text=_PRODUCTION_CMON_TEXT))
    assert repo.rows[0]["state"] == "NEEDS_INFORMATION"

    # Message 2: answers the missing-date question only -- zero canonical
    # writes against the real database.
    _post(_message_envelope(message_id="wamid.realdbB", text="Ya"))
    assert repo.rows[0]["state"] == "READY_FOR_CONFIRMATION"
    assert cmon_repo.find_by_source_reference(f"WHATSAPP::{repo.rows[0]['intake_id']}") is None

    # Message 3: final confirmation -- real canonical INSERT against real
    # Postgres.
    response = _post(_message_envelope(message_id="wamid.realdbC", text="Ya"))
    assert response.status_code == 200
    assert repo.rows[0]["state"] == "CONFIRMED"

    intake_id = repo.rows[0]["intake_id"]
    record = cmon_repo.find_by_source_reference(f"WHATSAPP::{intake_id}")
    assert record is not None
    assert record["asset_code"] == "211-P-13AR"
    assert record["asset_type"] == "PUMP"
    assert record["reading_date"].startswith("2026-08-29")
    assert record["mechanical_seal_leak_de"] is True
    assert record["mechanical_seal_leak_nde"] is True
    assert record["finding"] == "ditemukan kebocoran mechanical seal"
    assert record["condition_monitoring_schedule_code"] == "UNSCHEDULED::WHATSAPP"
    assert record["provenance"] == "WHATSAPP"
    assert record["source_reference"] == f"WHATSAPP::{intake_id}"

    reply = outbound.calls[-1][1]
    assert "berhasil disimpan" in reply
    # Date-format fix -- the real reading_date column is TIMESTAMP, so
    # record["reading_date"] above is correctly the full
    # "2026-08-29T00:00:00" (stored value/type untouched); the WhatsApp
    # reply text must show the date-only presentation form instead.
    assert "Tanggal: 2026-08-29\nKode:" in reply
    assert "T00:00:00" not in reply

    # Repeat final confirmation (plain "Ya") -- idempotent against the
    # real database, never a second canonical row.
    repeat = _post(_message_envelope(message_id="wamid.realdbD", text="Ya"))
    assert repeat.status_code == 200
    all_rows = cmon_repo.list_by_asset("211-P-13AR")
    assert len(all_rows) == 1

    # Task A: explicit confirmation-code retry against the same, now-
    # CONFIRMED row -- must resolve, disclose the existing canonical code,
    # and never write a second canonical record, against the real database.
    code = repo.rows[0]["confirmation_id"]
    canonical_code = record["condition_monitoring_reading_code"]
    explicit_retry = _post(_message_envelope(message_id="wamid.realdbE", text=f"YA {code}"))
    assert explicit_retry.status_code == 200
    assert outbound.calls[-1] == (SENDER_A, f"Condition Monitoring 211-P-13AR sudah tersimpan sebelumnya.\nKode: {canonical_code}")
    assert len(cmon_repo.list_by_asset("211-P-13AR")) == 1
