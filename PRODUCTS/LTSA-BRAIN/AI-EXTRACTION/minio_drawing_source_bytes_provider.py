"""MWO-LTSA-DRAWING-INPUT-R5A0B -- concrete, MinIO-backed
DrawingSourceBytesProvider (drawing_extraction_provider.py's own
Protocol, unchanged). This is the ONLY file in the Drawing pipeline
that imports the minio SDK for source-bytes retrieval, per that
module's own provider-independence boundary ("this service never
imports MinIO... directly").

Never falls back to the local filesystem. Never returns empty bytes
as if that were valid content (the Protocol's own explicit rule).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from minio import Minio
from minio.error import S3Error

_INGESTION_DIR = Path(__file__).resolve().parent.parent / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

# Section 3 -- Drawing-specific bound, deliberately separate from
# whatsapp_group_media_store.py's own (different-domain) 15 MB constant.
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


class KnowledgeSourceNotFound(Exception):
    """No knowledge_source_registry row for the given knowledge_source_id."""


class ObjectStorageKeyMissing(Exception):
    """The row exists but object_storage_key is NULL -- never registered
    to real object storage (e.g. a row created by an older/other path)."""


class ObjectNotFound(Exception):
    """object_storage_key is set but no such object exists in the
    configured bucket."""


class StorageUnavailable(Exception):
    """MinIO could not be reached, returned an unexpected error, or the
    retrieved payload was empty/oversized -- never treated as NotFound."""


class IntegrityMismatch(Exception):
    """Retrieved bytes' SHA-256 does not match
    knowledge_source_registry.file_hash."""


class MinioDrawingSourceBytesProvider:
    """Implements DrawingSourceBytesProvider.get_bytes() against a real
    MinIO/S3-compatible bucket. Bucket/client are injected -- this class
    never reads env vars itself (see minio_client_from_env() below for
    that, used only by real callers, never by tests)."""

    def __init__(self, runner: "DatabaseRunner", client: Minio, bucket: str) -> None:
        self._runner = runner
        self._client = client
        self._bucket = bucket

    def get_bytes(self, knowledge_source_id: str) -> tuple[bytes, str]:
        from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

        rows = _json_query(
            "SELECT object_storage_key, file_hash, media_type "
            "FROM knowledge_source_registry "
            f"WHERE knowledge_source_id = {_sql(knowledge_source_id)}",
            self._runner,
        )
        if not rows:
            raise KnowledgeSourceNotFound(knowledge_source_id)

        row = rows[0]
        object_key = row.get("object_storage_key")
        if not object_key:
            raise ObjectStorageKeyMissing(knowledge_source_id)

        try:
            response = self._client.get_object(self._bucket, object_key)
            try:
                data = response.read(MAX_DOWNLOAD_BYTES + 1)
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject", "NoSuchBucket"):
                raise ObjectNotFound(f"{knowledge_source_id}: {object_key}") from exc
            raise StorageUnavailable(f"{knowledge_source_id}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 -- connection-level, not an S3Error
            raise StorageUnavailable(f"{knowledge_source_id}: {exc}") from exc

        if not data:
            raise StorageUnavailable(f"{knowledge_source_id}: object retrieval returned empty bytes")
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise StorageUnavailable(f"{knowledge_source_id}: object exceeds bounded download limit")

        file_hash = row.get("file_hash")
        if file_hash:
            actual = hashlib.sha256(data).hexdigest()
            if actual != file_hash:
                raise IntegrityMismatch(f"{knowledge_source_id}: expected {file_hash}, got {actual}")

        media_type = row.get("media_type") or "application/octet-stream"
        return data, media_type


def minio_client_from_env() -> tuple[Minio, str]:
    """Builds a real Minio client + bucket name from the SAME env vars the
    runtime compose stack already defines (AI5R_MINIO_PUBLIC_URL,
    AI5R_MINIO_ROOT_USER, AI5R_MINIO_ROOT_PASSWORD) plus the one new
    Section 4 addition (AI5R_MINIO_DRAWING_BUCKET). Reads names only --
    never hardcodes a credential value. Not used by any test in this
    phase (tests inject their own disposable client)."""
    import os
    from urllib.parse import urlparse

    endpoint_url = os.environ["AI5R_MINIO_PUBLIC_URL"]
    parsed = urlparse(endpoint_url)
    client = Minio(
        parsed.netloc,
        access_key=os.environ["AI5R_MINIO_ROOT_USER"],
        secret_key=os.environ["AI5R_MINIO_ROOT_PASSWORD"],
        secure=parsed.scheme == "https",
    )
    bucket = os.environ["AI5R_MINIO_DRAWING_BUCKET"]
    return client, bucket


__all__ = [
    "MinioDrawingSourceBytesProvider",
    "minio_client_from_env",
    "MAX_DOWNLOAD_BYTES",
    "KnowledgeSourceNotFound",
    "ObjectStorageKeyMissing",
    "ObjectNotFound",
    "StorageUnavailable",
    "IntegrityMismatch",
]
