"""MWO-LTSA-DRAWING-INPUT-R5A0B -- KnowledgeSourceRegistrationService and
MinioDrawingSourceBytesProvider against a REAL, disposable Postgres and a
FAKE in-memory MinIO client (no real object storage anywhere in this file
-- see FakeMinioClient below). Same container/bootstrap/truncate pattern
as the other Drawing test files.
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
_AI_EXTRACTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "AI-EXTRACTION"
for _path in (_INGESTION_DIR, _AI_EXTRACTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from minio.error import S3Error  # noqa: E402
import minio_drawing_source_bytes_provider as bytes_provider_module  # noqa: E402
from minio_drawing_source_bytes_provider import (  # noqa: E402
    IntegrityMismatch,
    KnowledgeSourceNotFound,
    MinioDrawingSourceBytesProvider,
    ObjectNotFound,
    ObjectStorageKeyMissing,
    StorageUnavailable,
)
import knowledge_source_registration_service as registration_module  # noqa: E402
from knowledge_source_registration_service import (  # noqa: E402
    FileTooLarge,
    KnowledgeSourceRegistrationService,
    MimeMismatch,
    UnsupportedMedia,
    content_address,
    sanitize_filename,
)

_CONTAINER_NAME = "ai5r-test-drawing-source-registration-pg"
_USER = "ai5r"
_PASSWORD = "test-drawing-source-registration-password"
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
        "037_create_ltsa_finding_and_cm_measurement.sql",
        "038_create_engineering_drawing.sql",
        "039_create_engineering_drawing_attribute.sql",
    )
]

_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data
        self.closed = False

    def read(self, n: int = -1) -> bytes:
        return self._data if n < 0 else self._data[: n]

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        pass


def _s3_error(code: str) -> S3Error:
    return S3Error(
        response=None, code=code, message=code, resource=None, request_id=None, host_id=None,
    )


class FakeMinioClient:
    """In-memory stand-in for minio.Minio -- no network, no real storage,
    anywhere. Only the subset of the real client's API this pipeline
    actually calls is implemented."""

    def __init__(self):
        self._buckets: set[str] = set()
        self._objects: dict[tuple[str, str], bytes] = {}
        self.fail_get_with: Exception | None = None
        self.put_calls: list[tuple[str, str]] = []

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self._buckets

    def make_bucket(self, bucket: str) -> None:
        self._buckets.add(bucket)

    def put_object(self, bucket, object_name, data, length, content_type=None, **_kwargs) -> None:
        self._objects[(bucket, object_name)] = data.read(length)
        self.put_calls.append((bucket, object_name))

    def stat_object(self, bucket, object_name):
        if (bucket, object_name) not in self._objects:
            raise _s3_error("NoSuchKey")
        return object()

    def get_object(self, bucket, object_name, **_kwargs) -> _FakeResponse:
        if self.fail_get_with is not None:
            raise self.fail_get_with
        data = self._objects.get((bucket, object_name))
        if data is None:
            raise _s3_error("NoSuchKey")
        return _FakeResponse(data)


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", "-v", _CONTAINER_NAME], capture_output=True, text=True)
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
        subprocess.run(["docker", "rm", "-f", "-v", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script("TRUNCATE knowledge_source_registry RESTART IDENTITY CASCADE;")
    return r


@pytest.fixture
def minio_client():
    return FakeMinioClient()


@pytest.fixture
def service(runner, minio_client):
    return KnowledgeSourceRegistrationService(runner, minio_client, "ltsa-drawing-sources-test")


@pytest.fixture
def provider(runner, minio_client):
    return MinioDrawingSourceBytesProvider(runner, minio_client, "ltsa-drawing-sources-test")


# ---- registration: valid media ----------------------------------------


def test_register_valid_pdf(service, minio_client):
    result = service.register(_PDF_BYTES, "GA-196094-1.pdf", "application/pdf")
    assert result["knowledge_source_id"].startswith("KSR-")
    assert result["reused"] is False
    assert minio_client.bucket_exists("ltsa-drawing-sources-test")


@pytest.mark.parametrize(
    "data,mime_type",
    [(_JPEG_BYTES, "image/jpeg"), (_PNG_BYTES, "image/png"), (_WEBP_BYTES, "image/webp")],
)
def test_register_valid_image_types(service, data, mime_type):
    result = service.register(data, "photo.bin", mime_type)
    assert result["media_type"] == mime_type


# ---- registration: rejections ------------------------------------------


def test_register_rejects_oversized_file(service):
    oversized = b"%PDF-" + b"0" * (registration_module.MAX_UPLOAD_BYTES + 1) + b"%%EOF"
    with pytest.raises(FileTooLarge):
        service.register(oversized, "big.pdf", "application/pdf")


def test_register_rejects_mime_header_mismatch(service):
    with pytest.raises(MimeMismatch):
        service.register(_JPEG_BYTES, "fake.pdf", "application/pdf")


def test_register_rejects_unsupported_media(service):
    with pytest.raises(UnsupportedMedia):
        service.register(b"whatever", "model.step", "application/step")


def test_sanitize_filename_prevents_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\config") == "config"


# ---- content addressing -------------------------------------------------


def test_object_key_is_content_addressed_not_filename():
    sha256_hex, object_key = content_address(_PDF_BYTES, "application/pdf")
    assert object_key == f"{sha256_hex}/pdf"
    assert "GA-196094" not in object_key


def test_same_bytes_sequential_registration_reuses_id(service, minio_client):
    first = service.register(_PDF_BYTES, "first-name.pdf", "application/pdf")
    second = service.register(_PDF_BYTES, "second-name.pdf", "application/pdf")
    assert first["knowledge_source_id"] == second["knowledge_source_id"]
    assert second["reused"] is True
    # content-addressed key: only ONE object was ever actually uploaded
    assert len(minio_client.put_calls) == 1


def test_same_bytes_different_filename_keeps_first_provenance(service, runner):
    service.register(_PDF_BYTES, "original-name.pdf", "application/pdf")
    service.register(_PDF_BYTES, "renamed-copy.pdf", "application/pdf")
    from ltsa_pump_inventory_db_upsert import _json_query

    rows = _json_query("SELECT original_file_name FROM knowledge_source_registry", runner)
    assert len(rows) == 1  # one row, not two -- reuse, not duplication
    assert rows[0]["original_file_name"] == "original-name.pdf"


# ---- idempotency + concurrency (Section 7 -- honest, not hidden) -------


def test_sequential_idempotency_confirmed(service):
    ids = {service.register(_PDF_BYTES, f"name-{i}.pdf", "application/pdf")["knowledge_source_id"] for i in range(3)}
    assert len(ids) == 1  # SEQUENTIAL_IDEMPOTENCY=YES


def test_concurrent_registration_is_not_guaranteed_single_row(service, runner):
    """Documents the disclosed gap directly at the schema level: two
    transactions that both pass their own SELECT-for-existing check before
    either INSERTs (the real race a thread-level test can't reliably force
    against a fake in-memory client) end up each calling _insert() for the
    SAME file_hash/object_storage_key -- and the schema has no UNIQUE
    constraint to stop that. CONCURRENT_IDEMPOTENCY=NO, proven by showing
    the DB itself accepts both rows rather than rejecting the second."""
    sha256_hex, object_key = content_address(_PDF_BYTES, "application/pdf")
    service._insert("KSR-RACE-A", "a.pdf", sha256_hex, len(_PDF_BYTES), "application/pdf", object_key)
    service._insert("KSR-RACE-B", "b.pdf", sha256_hex, len(_PDF_BYTES), "application/pdf", object_key)

    from ltsa_pump_inventory_db_upsert import _json_query

    rows = _json_query(
        f"SELECT knowledge_source_id FROM knowledge_source_registry WHERE file_hash = '{sha256_hex}'", runner
    )
    assert len(rows) == 2  # the schema permitted a duplicate for identical content -- the honest gap


# ---- storage/DB compensation (Section 8) --------------------------------


def test_upload_succeeds_db_insert_fails_then_retry_succeeds(service, minio_client, runner):
    original_insert = service._insert
    call_count = {"n": 0}

    def _failing_insert(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated DB failure after upload")
        return original_insert(*args, **kwargs)

    service._insert = _failing_insert
    with pytest.raises(RuntimeError):
        service.register(_PDF_BYTES, "first-try.pdf", "application/pdf")

    # orphan object exists, was never deleted
    sha256_hex, object_key = content_address(_PDF_BYTES, "application/pdf")
    assert ("ltsa-drawing-sources-test", object_key) in minio_client._objects
    assert len(minio_client.put_calls) == 1  # retry must not re-upload

    result = service.register(_PDF_BYTES, "retry.pdf", "application/pdf")
    assert result["reused"] is False
    assert len(minio_client.put_calls) == 1  # still just the one upload


# ---- provider: retrieval + failure classes ------------------------------


def test_provider_retrieves_registered_bytes(service, provider):
    reg = service.register(_PDF_BYTES, "GA-196094-1.pdf", "application/pdf")
    data, media_type = provider.get_bytes(reg["knowledge_source_id"])
    assert data == _PDF_BYTES
    assert media_type == "application/pdf"


def test_provider_missing_knowledge_source(provider):
    with pytest.raises(KnowledgeSourceNotFound):
        provider.get_bytes("KSR-DOES-NOT-EXIST")


def test_provider_missing_object_storage_key(provider, runner):
    runner.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) "
        "VALUES ('KSR-NO-KEY', 'DRAWING', 'No Key');"
    )
    with pytest.raises(ObjectStorageKeyMissing):
        provider.get_bytes("KSR-NO-KEY")


def test_provider_missing_object(provider, runner):
    runner.execute_script(
        "INSERT INTO knowledge_source_registry "
        "(knowledge_source_id, source_type, source_name, object_storage_key) "
        "VALUES ('KSR-GHOST', 'DRAWING', 'Ghost', 'deadbeef/pdf');"
    )
    with pytest.raises(ObjectNotFound):
        provider.get_bytes("KSR-GHOST")


def test_provider_storage_unavailable(service, provider, minio_client):
    reg = service.register(_PDF_BYTES, "x.pdf", "application/pdf")
    minio_client.fail_get_with = ConnectionError("simulated MinIO outage")
    with pytest.raises(StorageUnavailable):
        provider.get_bytes(reg["knowledge_source_id"])


def test_provider_integrity_mismatch(service, provider, runner):
    reg = service.register(_PDF_BYTES, "x.pdf", "application/pdf")
    runner.execute_script(
        "UPDATE knowledge_source_registry SET file_hash = 'not-the-real-hash' "
        f"WHERE knowledge_source_id = '{reg['knowledge_source_id']}';"
    )
    with pytest.raises(IntegrityMismatch):
        provider.get_bytes(reg["knowledge_source_id"])


def test_provider_bounded_download(service, provider, minio_client, monkeypatch):
    reg = service.register(_PDF_BYTES, "x.pdf", "application/pdf")
    monkeypatch.setattr(bytes_provider_module, "MAX_DOWNLOAD_BYTES", 4)
    with pytest.raises(StorageUnavailable):
        provider.get_bytes(reg["knowledge_source_id"])


def test_provider_no_local_filesystem_fallback(provider, minio_client, runner):
    """A storage failure must surface as StorageUnavailable, never silently
    resolved by reading anything from the local disk."""
    runner.execute_script(
        "INSERT INTO knowledge_source_registry "
        "(knowledge_source_id, source_type, source_name, object_storage_key) "
        "VALUES ('KSR-NOFALLBACK', 'DRAWING', 'x', 'irrelevant/pdf');"
    )
    minio_client.fail_get_with = RuntimeError("storage down")
    with pytest.raises(StorageUnavailable):
        provider.get_bytes("KSR-NOFALLBACK")


# ---- scope boundary (Section 6/9) ---------------------------------------


def test_registration_never_infers_artifact_class(service):
    result = service.register(_PDF_BYTES, "GA-196094-1.pdf", "application/pdf")
    assert "artifact_class" not in result
    assert set(result) == {"knowledge_source_id", "sha256", "media_type", "object_storage_key", "reused"}


def test_registration_module_never_imports_downstream_services():
    # Checks the module's own NAMESPACE (real import bindings), not its
    # source text -- the docstring itself names these services in prose
    # to explain the boundary, which a plain text search would misfire on.
    for forbidden in (
        "EngineeringDrawingExtractionStagingService",
        "EngineeringDrawingReviewService",
        "EngineeringDrawingPromotionService",
    ):
        assert not hasattr(registration_module, forbidden)
