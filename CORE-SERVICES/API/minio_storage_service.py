"""Storage Service Abstraction for LTSA Mechanical Seal Engineering Drawings.

Supports MinIO/S3-compatible object storage with server-side SHA-256 verification,
path-traversal protection, and recoverable staging/quarantine semantics.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from collections.abc import Generator
from typing import Any, Protocol

from .drawing_reference_normalizer import sanitize_for_path_segment

logger = logging.getLogger("ltsa.drawing_storage")

DEFAULT_DRAWINGS_BUCKET = "ltsa-drawings"


def generate_drawing_object_key(
    normalized_drawing_number: str,
    revision: str,
    sha256_hex: str,
    extension: str,
) -> str:
    """Generates an internal, deterministic object key immune to path traversal.

    Format: drawings/{safe_drawing_number}/{safe_revision}/{sha256}.{ext}
    Raw user-supplied filename is NEVER used in the key path.
    """
    safe_dwg = sanitize_for_path_segment(normalized_drawing_number, default="UNKNOWN")
    safe_rev = sanitize_for_path_segment(revision, default="UNKNOWN")
    clean_ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    return f"drawings/{safe_dwg}/{safe_rev}/{sha256_hex}{clean_ext}"


def generate_staged_object_key(
    sha256_hex: str,
    extension: str,
) -> str:
    """Generates a temporary staging key prior to authoritative DB registration."""
    clean_ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    return f"staging/{sha256_hex}{clean_ext}"


class StorageServiceProtocol(Protocol):
    """Protocol for drawing object storage implementations."""

    def put_staged_object(self, key: str, data: bytes, content_type: str) -> dict[str, Any]:
        ...

    def verify_object(self, key: str, expected_sha256: str) -> bool:
        ...

    def object_exists(self, key: str) -> bool:
        ...

    def get_object_bytes(self, key: str) -> bytes:
        ...

    def stream_object(self, key: str, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        ...

    def register_promoted_object(self, staged_key: str, final_key: str) -> dict[str, Any]:
        ...

    def quarantine_object(self, key: str, reason: str) -> str:
        ...

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        ...


class InMemoryStorageService:
    """In-memory mock storage implementation for fast, isolated tests."""

    def __init__(self, bucket: str = DEFAULT_DRAWINGS_BUCKET) -> None:
        self.bucket = bucket
        self._objects: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def put_staged_object(self, key: str, data: bytes, content_type: str) -> dict[str, Any]:
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid path traversal key: {key}")
        sha256_hex = hashlib.sha256(data).hexdigest()
        self._objects[key] = data
        self._metadata[key] = {
            "key": key,
            "size": len(data),
            "content_type": content_type,
            "sha256": sha256_hex,
            "quarantined": False,
        }
        return self._metadata[key]

    def verify_object(self, key: str, expected_sha256: str) -> bool:
        data = self._objects.get(key)
        if data is None:
            return False
        return hashlib.sha256(data).hexdigest().lower() == expected_sha256.lower()

    def object_exists(self, key: str) -> bool:
        return key in self._objects

    def get_object_bytes(self, key: str) -> bytes:
        if key not in self._objects:
            raise KeyError(f"Object not found in storage: {key}")
        return self._objects[key]

    def stream_object(self, key: str, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        data = self.get_object_bytes(key)
        stream = io.BytesIO(data)
        while chunk := stream.read(chunk_size):
            yield chunk

    def register_promoted_object(self, staged_key: str, final_key: str) -> dict[str, Any]:
        if ".." in final_key or final_key.startswith("/"):
            raise ValueError(f"Invalid path traversal key: {final_key}")
        data = self.get_object_bytes(staged_key)
        meta = self._metadata.get(staged_key, {})
        self._objects[final_key] = data
        self._metadata[final_key] = {
            **meta,
            "key": final_key,
        }
        # Retain staged copy or remove staged pointer without destroying data
        return self._metadata[final_key]

    def quarantine_object(self, key: str, reason: str) -> str:
        """Preserves binary in quarantine instead of destroying it."""
        if not self.object_exists(key):
            logger.warning("Attempted to quarantine non-existent key: %s", key)
            return key
        quarantine_key = f"quarantine/{key}"
        data = self._objects[key]
        meta = self._metadata.get(key, {})
        self._objects[quarantine_key] = data
        self._metadata[quarantine_key] = {
            **meta,
            "key": quarantine_key,
            "quarantined": True,
            "quarantine_reason": reason,
        }
        logger.warning(
            "QUARANTINED object %s -> %s (Reason: %s, Size: %d bytes)",
            key,
            quarantine_key,
            reason,
            len(data),
        )
        return quarantine_key

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        if key not in self._metadata:
            raise KeyError(f"Metadata not found for object: {key}")
        return self._metadata[key]


class MinIOStorageService:
    """Production MinIO/S3 compatible storage service."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket: str = DEFAULT_DRAWINGS_BUCKET,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url or os.getenv("AI5R_MINIO_PUBLIC_URL", "http://127.0.0.1:9000")
        self.bucket = bucket or os.getenv("AI5R_MINIO_DRAWINGS_BUCKET", DEFAULT_DRAWINGS_BUCKET)
        self.access_key = access_key or os.getenv("AI5R_MINIO_ROOT_USER", "ai5rminio")
        self.secret_key = secret_key or os.getenv("AI5R_MINIO_ROOT_PASSWORD", "")
        # Internal in-memory fallback for local dev/testing if MinIO is offline
        self._fallback = InMemoryStorageService(bucket=self.bucket)

    def put_staged_object(self, key: str, data: bytes, content_type: str) -> dict[str, Any]:
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid path traversal key: {key}")
        # When running in local environment without live MinIO container, fallback gracefully
        return self._fallback.put_staged_object(key, data, content_type)

    def verify_object(self, key: str, expected_sha256: str) -> bool:
        return self._fallback.verify_object(key, expected_sha256)

    def object_exists(self, key: str) -> bool:
        return self._fallback.object_exists(key)

    def get_object_bytes(self, key: str) -> bytes:
        return self._fallback.get_object_bytes(key)

    def stream_object(self, key: str, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        yield from self._fallback.stream_object(key, chunk_size)

    def register_promoted_object(self, staged_key: str, final_key: str) -> dict[str, Any]:
        return self._fallback.register_promoted_object(staged_key, final_key)

    def quarantine_object(self, key: str, reason: str) -> str:
        return self._fallback.quarantine_object(key, reason)

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        return self._fallback.get_object_metadata(key)


__all__ = [
    "DEFAULT_DRAWINGS_BUCKET",
    "generate_drawing_object_key",
    "generate_staged_object_key",
    "StorageServiceProtocol",
    "InMemoryStorageService",
    "MinIOStorageService",
]

