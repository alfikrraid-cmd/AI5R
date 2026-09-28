"""MWO-LTSA-DRAWING-INPUT-R5A0B -- Engineering Drawing source
registration: raw bytes + an original filename -> a knowledge_source_registry
row backed by a real, content-addressed MinIO object.

Scope boundary (Section 6's own explicit instruction): this module ONLY
registers a source. It never imports EngineeringDrawingExtractionStagingService,
EngineeringDrawingReviewService, or EngineeringDrawingPromotionService, and it
never infers or writes an ARTIFACT_CLASS -- that classification belongs to
human review/promotion, never to an upload-time guess from a MIME type or
file extension.

Object identity is the SHA-256 of the bytes, never the filename (Section 3).
The knowledge_source_registry schema has no UNIQUE constraint on file_hash
or object_storage_key (verified by the R5A0B design audit) -- registration
is therefore only SEQUENTIALLY idempotent (a second call with identical
bytes, awaited before a third starts, reuses the same knowledge_source_id).
Two truly concurrent calls with identical bytes are NOT guaranteed to
collapse to one row; this is a disclosed, not a hidden, gap -- see this
MWO's own CONCURRENT_IDEMPOTENCY report. No migration is added here to
close it (an unapproved schema change is explicitly out of this phase's
scope).
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from minio import Minio
from minio.error import S3Error

_INGESTION_DIR = Path(__file__).resolve().parent.parent / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

# Section 3 -- required initial media only; CAD stays out of R5A0B scope.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

_MIME_EXTENSION = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_SOURCE_TYPE = "DRAWING"  # Section 2 -- already a legal knowledge_source_registry
# .source_type CHECK-constraint value; no schema change required.


class UnsupportedMedia(Exception):
    """declared_mime_type is not one of _MIME_EXTENSION's keys."""


class FileTooLarge(Exception):
    """len(file_bytes) exceeds MAX_UPLOAD_BYTES."""


class MimeMismatch(Exception):
    """declared_mime_type does not match the bytes' own magic-byte header."""


def _magic_bytes_match(data: bytes, declared_mime_type: str) -> bool:
    """Same signatures whatsapp_group_media_store.validate_media_file()
    already checks for JPEG/PNG/WEBP/PDF -- mirrored, not re-derived."""
    if declared_mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if declared_mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if declared_mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if declared_mime_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return False


def sanitize_filename(name: str) -> str:
    """Mirrors whatsapp_group_media_store.sanitize_filename()'s own
    discipline (never used for object identity -- provenance only)."""
    base = os.path.basename(name or "").strip()
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    clean = clean.strip("._")
    if not clean:
        clean = "source"
    if len(clean) > 100:
        stem, ext = os.path.splitext(clean)
        clean = stem[: 100 - len(ext)] + ext
    return clean


def content_address(file_bytes: bytes, mime_type: str) -> tuple[str, str]:
    """Returns (sha256_hex, object_key). object_key is NEVER derived from
    a filename -- Section 3's own explicit requirement."""
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
    extension = _MIME_EXTENSION[mime_type]
    return sha256_hex, f"{sha256_hex}/{extension}"


def ensure_bucket(client: Minio, bucket: str) -> None:
    """Idempotent bucket provisioning (Section 10) -- safe to call every
    time; never called against the running AI5R runtime MinIO by any test
    in this phase."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


class KnowledgeSourceRegistrationService:
    def __init__(self, runner: "DatabaseRunner", client: Minio, bucket: str) -> None:
        self._runner = runner
        self._client = client
        self._bucket = bucket

    def _find_existing(self, sha256_hex: str) -> dict | None:
        from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

        rows = _json_query(
            "SELECT knowledge_source_id, object_storage_key FROM knowledge_source_registry "
            f"WHERE source_type = {_sql(_SOURCE_TYPE)} AND file_hash = {_sql(sha256_hex)} "
            "ORDER BY created_at LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def _object_exists(self, object_key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, object_key)
            return True
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return False
            raise

    def register(self, file_bytes: bytes, original_file_name: str, declared_mime_type: str) -> dict:
        if declared_mime_type not in _MIME_EXTENSION:
            raise UnsupportedMedia(
                f"{declared_mime_type!r} is not supported in R5A0B "
                f"(supported: {sorted(_MIME_EXTENSION)})"
            )
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise FileTooLarge(f"{len(file_bytes)} bytes exceeds {MAX_UPLOAD_BYTES} byte limit")
        if not _magic_bytes_match(file_bytes, declared_mime_type):
            raise MimeMismatch(f"bytes do not match declared MIME type {declared_mime_type!r}")

        sha256_hex, object_key = content_address(file_bytes, declared_mime_type)
        safe_name = sanitize_filename(original_file_name)

        existing = self._find_existing(sha256_hex)

        ensure_bucket(self._client, self._bucket)
        if not self._object_exists(object_key):
            # put_object is itself idempotent for an identical key/content --
            # a concurrent duplicate upload of the SAME bytes just overwrites
            # the object with identical bytes, never a collision (Section 3).
            self._client.put_object(
                self._bucket,
                object_key,
                io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=declared_mime_type,
            )

        if existing is not None:
            # Section 4 -- reuse; self-heal a partial prior registration
            # (a row whose object_storage_key never got set) rather than
            # inserting a duplicate row for identical content.
            if not existing.get("object_storage_key"):
                self._update_object_storage_key(existing["knowledge_source_id"], object_key)
            return {
                "knowledge_source_id": existing["knowledge_source_id"],
                "sha256": sha256_hex,
                "media_type": declared_mime_type,
                "object_storage_key": object_key,
                "reused": True,
            }

        knowledge_source_id = f"KSR-{uuid.uuid4().hex[:16].upper()}"
        self._insert(knowledge_source_id, safe_name, sha256_hex, len(file_bytes), declared_mime_type, object_key)
        return {
            "knowledge_source_id": knowledge_source_id,
            "sha256": sha256_hex,
            "media_type": declared_mime_type,
            "object_storage_key": object_key,
            "reused": False,
        }

    def _update_object_storage_key(self, knowledge_source_id: str, object_key: str) -> None:
        from ltsa_pump_inventory_db_upsert import _sql  # noqa: E402

        self._runner.execute_script(
            "UPDATE knowledge_source_registry SET object_storage_key = "
            f"{_sql(object_key)}, updated_at = NOW() "
            f"WHERE knowledge_source_id = {_sql(knowledge_source_id)};"
        )

    def _insert(
        self,
        knowledge_source_id: str,
        safe_name: str,
        sha256_hex: str,
        file_size: int,
        media_type: str,
        object_key: str,
    ) -> None:
        from ltsa_pump_inventory_db_upsert import _sql  # noqa: E402

        self._runner.execute_script(
            "INSERT INTO knowledge_source_registry "
            "(knowledge_source_id, source_type, source_name, original_file_name, "
            "verification_status, file_hash, file_size, media_type, object_storage_key) "
            f"VALUES ({_sql(knowledge_source_id)}, {_sql(_SOURCE_TYPE)}, {_sql(safe_name)}, "
            f"{_sql(safe_name)}, 'DRAFT', {_sql(sha256_hex)}, {_sql(file_size)}, "
            f"{_sql(media_type)}, {_sql(object_key)});"
        )


__all__ = [
    "KnowledgeSourceRegistrationService",
    "content_address",
    "sanitize_filename",
    "ensure_bucket",
    "MAX_UPLOAD_BYTES",
    "UnsupportedMedia",
    "FileTooLarge",
    "MimeMismatch",
]
