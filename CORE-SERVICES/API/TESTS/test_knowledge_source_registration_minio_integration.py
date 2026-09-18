"""MWO-LTSA-DRAWING-INPUT-R5A0B -- KnowledgeSourceRegistrationService and
MinioDrawingSourceBytesProvider against a REAL, disposable MinIO server
AND a REAL, disposable Postgres -- proving the actual `minio` SDK client
(not the fake used by test_knowledge_source_registration_service.py)
round-trips real bytes correctly. Same disposable-container-with-teardown
discipline as every other Drawing test file. Never touches the running
AI5R runtime MinIO/Postgres or their credentials/buckets.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest
from minio import Minio

_API_DIR = Path(__file__).resolve().parents[1]
_CORE_SERVICES_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_SERVICES_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
_AI_EXTRACTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "AI-EXTRACTION"
for _path in (_INGESTION_DIR, _AI_EXTRACTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from minio_drawing_source_bytes_provider import (  # noqa: E402
    IntegrityMismatch,
    MinioDrawingSourceBytesProvider,
    ObjectNotFound,
)
from knowledge_source_registration_service import (  # noqa: E402
    KnowledgeSourceRegistrationService,
    content_address,
)

_MINIO_CONTAINER = "ai5r-test-drawing-minio-roundtrip"
_MINIO_USER = "ai5r-test-minio-user"
_MINIO_PASSWORD = "ai5r-test-minio-password"
_BUCKET = "ai5r-test-drawing-sources"

_PG_CONTAINER = "ai5r-test-drawing-minio-roundtrip-pg"
_PG_USER = "ai5r"
_PG_PASSWORD = "test-drawing-minio-roundtrip-password"
_PG_DATABASE = "ltsa_brain"
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
        "037_create_ltsa_finding_and_cm_measurement.sql",
        "038_create_engineering_drawing.sql",
        "039_create_engineering_drawing_attribute.sql",
    )
]

# Harmless, minimal, synthetic PDF fixture bytes -- NEVER GA-196094-1.pdf.
_TEST_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"


@pytest.fixture(scope="module")
def minio_port():
    subprocess.run(["docker", "rm", "-f", "-v", _MINIO_CONTAINER], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _MINIO_CONTAINER,
            "-e", f"MINIO_ROOT_USER={_MINIO_USER}",
            "-e", f"MINIO_ROOT_PASSWORD={_MINIO_PASSWORD}",
            "-p", "127.0.0.1::9000",
            "minio/minio:RELEASE.2025-02-28T09-55-16Z",
            "server", "/data",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _MINIO_CONTAINER, "9000/tcp"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        host_port = int(port_output.rsplit(":", 1)[1])

        client = Minio(f"127.0.0.1:{host_port}", access_key=_MINIO_USER, secret_key=_MINIO_PASSWORD, secure=False)
        last_error: Exception | None = None
        for _ in range(30):
            try:
                client.list_buckets()
                last_error = None
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(1)
        if last_error is not None:
            raise RuntimeError(f"Test MinIO never became ready: {last_error}")

        yield host_port
    finally:
        subprocess.run(["docker", "rm", "-f", "-v", _MINIO_CONTAINER], capture_output=True, text=True)


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", "-v", _PG_CONTAINER], capture_output=True, text=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _PG_CONTAINER,
            "-e", f"POSTGRES_USER={_PG_USER}",
            "-e", f"POSTGRES_PASSWORD={_PG_PASSWORD}",
            "-e", f"POSTGRES_DB={_PG_DATABASE}",
            "-p", "127.0.0.1::5432",
            "postgres:16-alpine",
        ],
        check=True, capture_output=True, text=True,
    )
    try:
        port_output = subprocess.run(
            ["docker", "port", _PG_CONTAINER, "5432/tcp"], check=True, capture_output=True, text=True,
        ).stdout.strip()
        host_port = int(port_output.rsplit(":", 1)[1])

        probe = DatabaseRunner(
            DatabaseConfig(host="127.0.0.1", port=host_port, user=_PG_USER, password=_PG_PASSWORD, database=_PG_DATABASE)
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
        subprocess.run(["docker", "rm", "-f", "-v", _PG_CONTAINER], capture_output=True, text=True)


@pytest.fixture
def minio_client(minio_port):
    return Minio(f"127.0.0.1:{minio_port}", access_key=_MINIO_USER, secret_key=_MINIO_PASSWORD, secure=False)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_PG_USER, password=_PG_PASSWORD, database=_PG_DATABASE)
    )
    r.execute_script("TRUNCATE knowledge_source_registry RESTART IDENTITY CASCADE;")
    return r


@pytest.fixture
def service(runner, minio_client):
    return KnowledgeSourceRegistrationService(runner, minio_client, _BUCKET)


@pytest.fixture
def provider(runner, minio_client):
    return MinioDrawingSourceBytesProvider(runner, minio_client, _BUCKET)


def test_real_minio_roundtrip(service, provider, minio_client, runner):
    # 1-3: register against real MinIO + real Postgres.
    result = service.register(_TEST_PDF_BYTES, "harmless-fixture.pdf", "application/pdf")

    # 4: object physically exists at <sha256>/pdf in the real bucket.
    sha256_hex, expected_key = content_address(_TEST_PDF_BYTES, "application/pdf")
    assert result["object_storage_key"] == expected_key
    stat = minio_client.stat_object(_BUCKET, expected_key)
    assert stat.size == len(_TEST_PDF_BYTES)

    # 5: knowledge_source_registry stores the real object_storage_key.
    from ltsa_pump_inventory_db_upsert import _json_query

    rows = _json_query(
        f"SELECT object_storage_key, file_hash FROM knowledge_source_registry "
        f"WHERE knowledge_source_id = '{result['knowledge_source_id']}'",
        runner,
    )
    assert rows[0]["object_storage_key"] == expected_key
    assert rows[0]["file_hash"] == sha256_hex

    # 6-8: provider retrieves the real bytes back, hash matches, bytes match exactly.
    data, media_type = provider.get_bytes(result["knowledge_source_id"])
    assert data == _TEST_PDF_BYTES
    assert media_type == "application/pdf"
    import hashlib

    assert hashlib.sha256(data).hexdigest() == sha256_hex

    # 9-10: second sequential registration reuses the same id, no second object.
    second = service.register(_TEST_PDF_BYTES, "different-name.pdf", "application/pdf")
    assert second["knowledge_source_id"] == result["knowledge_source_id"]
    objects = list(minio_client.list_objects(_BUCKET, recursive=True))
    assert len(objects) == 1


def test_real_minio_object_not_found(provider, runner):
    runner.execute_script(
        "INSERT INTO knowledge_source_registry "
        "(knowledge_source_id, source_type, source_name, object_storage_key) "
        "VALUES ('KSR-RT-GHOST', 'DRAWING', 'Ghost', 'never-uploaded/pdf');"
    )
    with pytest.raises(ObjectNotFound):
        provider.get_bytes("KSR-RT-GHOST")


def test_real_minio_integrity_mismatch(service, provider, runner, minio_client):
    result = service.register(_TEST_PDF_BYTES, "x.pdf", "application/pdf")
    # Corrupt the real object in place -- same key, different bytes.
    import io

    minio_client.put_object(
        _BUCKET, result["object_storage_key"], io.BytesIO(b"CORRUPTED"), length=len(b"CORRUPTED"),
        content_type="application/pdf",
    )
    with pytest.raises(IntegrityMismatch):
        provider.get_bytes(result["knowledge_source_id"])
