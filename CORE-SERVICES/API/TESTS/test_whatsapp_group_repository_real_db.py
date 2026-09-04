"""
MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2A -- proves
WhatsAppGroupAuthorizationRepository against a REAL, disposable,
published-port Postgres running the actual migration 032 schema -- the
same self-contained `docker run postgres:16-alpine` discipline
test_pm_occurrence_repository_real_db.py already established (no
docker-compose, no .env.verify.local -- only the `docker` CLI itself,
which GitHub-hosted runners already have).

Only migration 032 is bootstrapped (whatsapp_group_authorization,
whatsapp_group_message_seen) -- these two tables have no foreign key onto
any other canonical table, so the full CANONICAL_SCHEMA.sql/migration
chain is not needed here, unlike the PM occurrence test's own broader
dependency chain.

"Restart does not lose group authorization" / "duplicate message ignored
after repository/service restart" are proven literally, not simulated:
a SECOND, independent WhatsAppGroupAuthorizationRepository instance
(a fresh Python object, standing in for a fresh process) is pointed at
the SAME still-running container and asked to read back state a FIRST
instance wrote -- this is the actual, real thing "restart-safe" means
for a stateless application process talking to Postgres: the row lives
in the database, not in either instance's memory.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
for path in (_CORE_SERVICES_DIR, _INGESTION_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.whatsapp_group_agent_service import GroupNotFoundError  # noqa: E402
from API.whatsapp_group_repository_postgres import WhatsAppGroupAuthorizationRepository  # noqa: E402

_CONTAINER_NAME = "ai5r-test-whatsapp-group-agent-pg"
_USER = "ai5r"
_PASSWORD = "test-whatsapp-group-agent-password"
_DATABASE = "ai5r_test"
_MIGRATION = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "DATABASE" / "MIGRATIONS" / "032_create_whatsapp_group_authorization.sql"


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
        bootstrap_schema(probe, _MIGRATION)
        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


def _repo(host_port: int) -> WhatsAppGroupAuthorizationRepository:
    # A fresh instance every call -- standing in for a fresh process/
    # container recreation, never sharing Python-level state with any
    # other instance in this test file.
    runner = DatabaseRunner(DatabaseConfig(host="127.0.0.1", port=host_port, user=_USER, password=_PASSWORD, database=_DATABASE))
    return WhatsAppGroupAuthorizationRepository(runner)


def test_pending_persists_and_survives_a_simulated_restart(pg_port):
    group_hash = "hash-pending-001"
    _repo(pg_port).register_group(group_hash=group_hash, display_label="TAP Group A", registered_by="admin-1")
    # Simulated restart: a brand-new repository instance, same database.
    record = _repo(pg_port).find_group_by_hash(group_hash)
    assert record is not None
    assert record.status == "PENDING"


def test_active_persists_with_scope_and_survives_a_simulated_restart(pg_port):
    group_hash = "hash-active-001"
    _repo(pg_port).register_group(group_hash=group_hash, display_label="TAP Group B", registered_by="admin-1")
    _repo(pg_port).activate_group(group_hash=group_hash, activated_by="admin-2", allowed_scope=frozenset({"HOC"}))
    record = _repo(pg_port).find_group_by_hash(group_hash)
    assert record.status == "ACTIVE"
    assert record.allowed_scope == frozenset({"HOC"})


def test_disabled_persists_and_survives_a_simulated_restart(pg_port):
    group_hash = "hash-disabled-001"
    _repo(pg_port).register_group(group_hash=group_hash, display_label="TAP Group C", registered_by="admin-1")
    _repo(pg_port).activate_group(group_hash=group_hash, activated_by="admin-2")
    _repo(pg_port).disable_group(group_hash=group_hash, disabled_by="admin-3")
    record = _repo(pg_port).find_group_by_hash(group_hash)
    assert record.status == "DISABLED"


def test_actor_attribution_preserved_across_the_full_lifecycle(pg_port):
    group_hash = "hash-attribution-001"
    registered = _repo(pg_port).register_group(group_hash=group_hash, display_label="TAP Group D", registered_by="admin-alpha")
    assert registered["registered_by"] == "admin-alpha"
    activated = _repo(pg_port).activate_group(group_hash=group_hash, activated_by="admin-beta")
    assert activated["activated_by"] == "admin-beta"
    assert activated["registered_by"] == "admin-alpha"  # never overwritten by a later actor
    disabled = _repo(pg_port).disable_group(group_hash=group_hash, disabled_by="admin-gamma")
    assert disabled["disabled_by"] == "admin-gamma"
    assert disabled["activated_by"] == "admin-beta"


def test_activate_unknown_group_raises_not_found(pg_port):
    with pytest.raises(GroupNotFoundError):
        _repo(pg_port).activate_group(group_hash="does-not-exist", activated_by="admin-1")


def test_disable_unknown_group_raises_not_found(pg_port):
    with pytest.raises(GroupNotFoundError):
        _repo(pg_port).disable_group(group_hash="does-not-exist", disabled_by="admin-1")


def test_dedupe_ledger_is_atomic_and_survives_a_simulated_restart(pg_port):
    provider_message_id = "wamid.REALDB-DEDUPE-1"
    first = _repo(pg_port).record_seen_message(provider_message_id)
    # A brand-new repository instance (simulated restart) must still see
    # the same id as already-seen -- the ledger lives in Postgres, not in
    # either instance's memory.
    second = _repo(pg_port).record_seen_message(provider_message_id)
    assert first is True
    assert second is False


def test_dedupe_retention_is_bounded_and_prunable(pg_port):
    repo = _repo(pg_port)
    repo.record_seen_message("wamid.RETENTION-OLD")
    runner = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    # Backdate the row to simulate age, rather than waiting real days.
    # execute_script (not query_scalar): a bare UPDATE with no RETURNING
    # clause produces no result set to fetch.
    runner.execute_script(
        "UPDATE public.whatsapp_group_message_seen SET seen_at = now() - interval '31 days' "
        "WHERE provider_message_id = 'wamid.RETENTION-OLD';"
    )
    repo.record_seen_message("wamid.RETENTION-FRESH")
    removed = repo.prune_seen_messages_older_than(30)
    assert removed == 1
    # Old id is gone from the ledger -- a redelivery of it now looks new
    # (acceptable: retention is bounded by the real-world redelivery
    # window, not infinite).
    assert repo.record_seen_message("wamid.RETENTION-OLD") is True
    # Fresh id is untouched by pruning.
    assert repo.record_seen_message("wamid.RETENTION-FRESH") is False


def test_dedupe_ledger_does_not_store_message_body(pg_port):
    # Structural guarantee: the table this repository writes to has no
    # column capable of holding a message body at all (see migration 032
    # -- only provider_message_id and seen_at). Confirmed directly against
    # the real schema, not assumed.
    runner = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    columns = runner.query_scalar(
        "SELECT COALESCE(json_agg(column_name)::text, '[]') FROM information_schema.columns "
        "WHERE table_name = 'whatsapp_group_message_seen'"
    )
    import json as _json

    assert set(_json.loads(columns)) == {"provider_message_id", "seen_at"}
