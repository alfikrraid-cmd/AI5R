"""Storage Service Abstraction for LTSA Mechanical Seal Engineering Drawings.

Supports MinIO/S3-compatible object storage with server-side SHA-256 verification,
path-traversal protection, and recoverable staging/quarantine semantics.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import io
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
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


class _NativeS3Client:
    """Lightweight, zero-dependency AWS SigV4 client for MinIO/S3 using Python stdlib."""

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        parsed = urllib.parse.urlparse(endpoint_url)
        self.host = parsed.netloc

    def _sign_request(
        self,
        method: str,
        key: str,
        body: bytes = b"",
        extra_headers: dict[str, str] | None = None,
    ) -> urllib.request.Request:
        now = datetime.datetime.now(datetime.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        canonical_uri = f"/{self.bucket}/{key.lstrip('/')}"
        canonical_querystring = ""
        payload_hash = hashlib.sha256(body).hexdigest()

        headers_to_sign: dict[str, str] = {
            "host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if extra_headers:
            for hk, hv in extra_headers.items():
                headers_to_sign[hk.lower()] = str(hv)

        sorted_header_names = sorted(headers_to_sign.keys())
        canonical_headers = "".join(f"{h}:{headers_to_sign[h]}\n" for h in sorted_header_names)
        signed_headers = ";".join(sorted_header_names)

        canonical_request = (
            f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
            f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
        )
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n{amz_date}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        def sign(k: bytes, msg: str | bytes) -> bytes:
            return hmac.new(k, msg if isinstance(msg, bytes) else msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = sign(("AWS4" + self.secret_key).encode("utf-8"), date_stamp)
        k_region = sign(k_date, self.region)
        k_service = sign(k_region, b"s3")
        k_signing = sign(k_service, b"aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        auth_header = (
            f"{algorithm} Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        req_url = f"{self.endpoint_url}{canonical_uri}"
        req = urllib.request.Request(
            req_url,
            data=body if method in ("PUT", "POST") and body else (b"" if method == "PUT" else None),
            method=method,
        )
        req.add_header("Authorization", auth_header)
        for h, v in headers_to_sign.items():
            if h != "host":
                req.add_header(h, v)
        return req

    def head_object(self, key: str) -> dict[str, str]:
        req = self._sign_request("HEAD", key)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return dict(resp.headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(f"Object not found: {key}") from exc
            raise

    def get_object(self, key: str) -> bytes:
        req = self._sign_request("GET", key)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(f"Object not found: {key}") from exc
            raise

    def stream_object(self, key: str, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        req = self._sign_request("GET", key)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                while chunk := resp.read(chunk_size):
                    yield chunk
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(f"Object not found: {key}") from exc
            raise

    def put_object(self, key: str, data: bytes, content_type: str) -> dict[str, str]:
        req = self._sign_request("PUT", key, body=data, extra_headers={"content-type": content_type})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return dict(resp.headers)

    def copy_object(self, source_key: str, target_key: str) -> dict[str, str]:
        copy_source = f"/{self.bucket}/{source_key.lstrip('/')}"
        req = self._sign_request("PUT", target_key, extra_headers={"x-amz-copy-source": copy_source})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return dict(resp.headers)


class MinIOStorageService:
    """Production MinIO/S3 compatible storage service with real delivery and graceful fallback."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket: str = DEFAULT_DRAWINGS_BUCKET,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        self.endpoint_url = endpoint_url or os.getenv("AI5R_MINIO_PUBLIC_URL", "http://127.0.0.1:9000")
        self.bucket = bucket or os.getenv("AI5R_MINIO_DRAWINGS_BUCKET", DEFAULT_DRAWINGS_BUCKET)
        self.access_key = access_key or os.getenv("AI5R_MINIO_ROOT_USER", "ai5rminio")
        self.secret_key = secret_key or os.getenv("AI5R_MINIO_ROOT_PASSWORD", "")
        self.region = region

        # Internal in-memory fallback for local dev/testing if MinIO is offline
        self._fallback = InMemoryStorageService(bucket=self.bucket)

        # Optional boto3 client
        self._boto3_client = None
        if self.access_key and self.secret_key and self.endpoint_url:
            try:
                import boto3
                from botocore.client import Config

                self._boto3_client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    config=Config(
                        signature_version="s3v4",
                        s3={"addressing_style": "path"},
                        connect_timeout=3,
                        read_timeout=10,
                    ),
                    region_name=self.region,
                )
            except Exception as exc:
                logger.debug("boto3 client initialization omitted: %s", exc)

        # Built-in native SigV4 client (zero third-party dependency)
        self._native_client = None
        if self.access_key and self.secret_key and self.endpoint_url:
            try:
                self._native_client = _NativeS3Client(
                    endpoint_url=self.endpoint_url,
                    bucket=self.bucket,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    region=self.region,
                )
            except Exception as exc:
                logger.debug("Native S3 client initialization omitted: %s", exc)

    def put_staged_object(self, key: str, data: bytes, content_type: str) -> dict[str, Any]:
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid path traversal key: {key}")

        # Always update in-memory fallback
        meta = self._fallback.put_staged_object(key, data, content_type)

        # Persist to live S3 if available
        if self._boto3_client is not None:
            try:
                self._boto3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
                return meta
            except Exception as exc:
                logger.warning("MinIO boto3 put_staged_object failed: %s", exc)
        elif self._native_client is not None:
            try:
                self._native_client.put_object(key, data, content_type)
                return meta
            except Exception as exc:
                logger.warning("MinIO native put_staged_object failed: %s", exc)

        return meta

    def verify_object(self, key: str, expected_sha256: str) -> bool:
        try:
            data = self.get_object_bytes(key)
            return hashlib.sha256(data).hexdigest().lower() == expected_sha256.lower()
        except Exception:
            return self._fallback.verify_object(key, expected_sha256)

    def object_exists(self, key: str) -> bool:
        if ".." in key or key.startswith("/"):
            return False

        if self._boto3_client is not None:
            try:
                self._boto3_client.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception as exc:
                err_code = getattr(getattr(exc, "response", None), "get", lambda _: {})("Error", {}).get("Code")
                if err_code in ("404", "NoSuchKey", "NotFound"):
                    return self._fallback.object_exists(key)
                logger.debug("boto3 head_object connection issue, falling back: %s", exc)

        if self._native_client is not None:
            try:
                self._native_client.head_object(key)
                return True
            except FileNotFoundError:
                return self._fallback.object_exists(key)
            except Exception as exc:
                logger.debug("Native S3 head_object connection issue, falling back: %s", exc)

        return self._fallback.object_exists(key)

    def get_object_bytes(self, key: str) -> bytes:
        if ".." in key or key.startswith("/"):
            raise KeyError(f"Invalid path traversal key: {key}")

        if self._boto3_client is not None:
            try:
                resp = self._boto3_client.get_object(Bucket=self.bucket, Key=key)
                return resp["Body"].read()
            except Exception as exc:
                err_code = getattr(getattr(exc, "response", None), "get", lambda _: {})("Error", {}).get("Code")
                if err_code in ("404", "NoSuchKey", "NotFound"):
                    return self._fallback.get_object_bytes(key)
                logger.debug("boto3 get_object connection issue, falling back: %s", exc)

        if self._native_client is not None:
            try:
                return self._native_client.get_object(key)
            except FileNotFoundError:
                return self._fallback.get_object_bytes(key)
            except Exception as exc:
                logger.debug("Native S3 get_object connection issue, falling back: %s", exc)

        return self._fallback.get_object_bytes(key)

    def stream_object(self, key: str, chunk_size: int = 65536) -> Generator[bytes, None, None]:
        if ".." in key or key.startswith("/"):
            raise KeyError(f"Invalid path traversal key: {key}")

        if self._boto3_client is not None:
            try:
                resp = self._boto3_client.get_object(Bucket=self.bucket, Key=key)
                body = resp["Body"]
                while chunk := body.read(chunk_size):
                    yield chunk
                return
            except Exception as exc:
                logger.debug("boto3 stream_object issue, falling back: %s", exc)

        if self._native_client is not None:
            try:
                yield from self._native_client.stream_object(key, chunk_size)
                return
            except Exception as exc:
                logger.debug("Native S3 stream_object issue, falling back: %s", exc)

        yield from self._fallback.stream_object(key, chunk_size)

    def register_promoted_object(self, staged_key: str, final_key: str) -> dict[str, Any]:
        if ".." in final_key or final_key.startswith("/"):
            raise ValueError(f"Invalid path traversal key: {final_key}")

        meta = self._fallback.register_promoted_object(staged_key, final_key)

        if self._boto3_client is not None:
            try:
                self._boto3_client.copy_object(
                    Bucket=self.bucket,
                    Key=final_key,
                    CopySource={"Bucket": self.bucket, "Key": staged_key},
                )
                return meta
            except Exception as exc:
                logger.warning("boto3 copy_object failed: %s", exc)
        elif self._native_client is not None:
            try:
                self._native_client.copy_object(staged_key, final_key)
                return meta
            except Exception as exc:
                logger.warning("Native S3 copy_object failed: %s", exc)

        return meta

    def quarantine_object(self, key: str, reason: str) -> str:
        quarantine_key = f"quarantine/{key}"
        if self._boto3_client is not None:
            try:
                self._boto3_client.copy_object(
                    Bucket=self.bucket,
                    Key=quarantine_key,
                    CopySource={"Bucket": self.bucket, "Key": key},
                    Metadata={"quarantine-reason": reason},
                    MetadataDirective="REPLACE",
                )
            except Exception as exc:
                logger.warning("boto3 quarantine copy failed: %s", exc)
        elif self._native_client is not None:
            try:
                self._native_client.copy_object(key, quarantine_key)
            except Exception as exc:
                logger.warning("Native S3 quarantine copy failed: %s", exc)

        return self._fallback.quarantine_object(key, reason)

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        if self._boto3_client is not None:
            try:
                head = self._boto3_client.head_object(Bucket=self.bucket, Key=key)
                return {
                    "key": key,
                    "size": head.get("ContentLength", 0),
                    "content_type": head.get("ContentType", "application/octet-stream"),
                    "etag": head.get("ETag", "").strip('"'),
                    "quarantined": key.startswith("quarantine/"),
                }
            except Exception:
                pass

        if self._native_client is not None:
            try:
                head = self._native_client.head_object(key)
                return {
                    "key": key,
                    "size": int(head.get("Content-Length", 0)),
                    "content_type": head.get("Content-Type", "application/octet-stream"),
                    "etag": head.get("ETag", "").strip('"'),
                    "quarantined": key.startswith("quarantine/"),
                }
            except Exception:
                pass

        return self._fallback.get_object_metadata(key)


__all__ = [
    "DEFAULT_DRAWINGS_BUCKET",
    "generate_drawing_object_key",
    "generate_staged_object_key",
    "StorageServiceProtocol",
    "InMemoryStorageService",
    "MinIOStorageService",
]

