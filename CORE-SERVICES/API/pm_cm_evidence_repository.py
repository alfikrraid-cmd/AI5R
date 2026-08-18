"""MWO-LTSA-PM-CM-INTAKE-001 -- evidence attachments for PM Occurrence /
Condition Monitoring Reading records. See migration 014's own header for
why file bytes live in Postgres BYTEA (no object-storage mechanism exists
anywhere in this repository).

Phase 22 (file security): validated here, not trusted from the client --
content_type must be one of a small real allowlist (JPG/JPEG/PNG/PDF,
Phase 6's own explicit list) and file_size_bytes is capped, both checked
BEFORE any bytes are written. filename is stored as an opaque label only
(never used to build a filesystem path -- there is no filesystem path,
bytes live in a database column), so filename-based path traversal is
structurally impossible here, not merely sanitized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

# Phase 6's own explicit list -- JPG/JPEG/PNG/PDF only. image/jpg is a
# common but non-standard alias browsers/phones sometimes send; accepted
# alongside the correct image/jpeg so a real photo upload is never
# rejected on a technicality.
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/jpg", "image/png", "application/pdf"})
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB -- generous for a phone photo/scanned PDF, not unbounded
ALLOWED_CATEGORIES = frozenset({"PHOTO", "REPORT", "MEASUREMENT", "OTHER"})

_SELECT_COLUMNS = (
    "evidence_id, record_type, record_code, file_name, content_type, "
    "file_size_bytes, category, source, uploaded_by, uploaded_at"
)  # file_data (the bytes) is deliberately never in the default list select -- see get_file_data


class UnsupportedContentTypeError(ValueError):
    """Raised when content_type is not in ALLOWED_CONTENT_TYPES."""


class FileTooLargeError(ValueError):
    """Raised when the upload exceeds MAX_FILE_SIZE_BYTES."""


def validate_upload(*, content_type: str, file_size_bytes: int) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedContentTypeError(
            f"unsupported content type {content_type!r} -- allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
        )
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(f"file is {file_size_bytes} bytes, exceeds the {MAX_FILE_SIZE_BYTES}-byte limit")


class PMCMEvidenceRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create(
        self,
        *,
        record_type: str,
        record_code: str,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
        category: str | None,
        source: str,
        uploaded_by: str,
    ) -> dict:
        validate_upload(content_type=content_type, file_size_bytes=len(file_bytes))
        # bytea literal: \x-prefixed hex, the standard PostgreSQL text
        # encoding for a byte string passed through a plain SQL literal
        # (no parameterized-query layer exists in this DatabaseRunner --
        # same constraint _sql() already works within for every other
        # value type).
        hex_literal = f"'\\x{file_bytes.hex()}'::bytea"
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO pm_cm_evidence "
                "(record_type, record_code, file_name, content_type, file_size_bytes, "
                "file_data, category, source, uploaded_by) VALUES "
                f"({_sql(record_type)}, {_sql(record_code)}, {_sql(file_name)}, {_sql(content_type)}, "
                f"{len(file_bytes)}, {hex_literal}, {_sql(category)}, {_sql(source)}, {_sql(uploaded_by)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def list_for_record(self, record_type: str, record_code: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM pm_cm_evidence "
            f"WHERE record_type = {_sql(record_type)} AND record_code = {_sql(record_code)} "
            "ORDER BY uploaded_at ASC",
            self._runner,
        )

    def get_file_data(self, evidence_id: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS}, encode(file_data, 'base64') AS file_data_base64 "
            f"FROM pm_cm_evidence WHERE evidence_id = {_sql(evidence_id)}",
            self._runner,
        )
        return rows[0] if rows else None


__all__ = [
    "PMCMEvidenceRepository",
    "ALLOWED_CONTENT_TYPES",
    "MAX_FILE_SIZE_BYTES",
    "ALLOWED_CATEGORIES",
    "UnsupportedContentTypeError",
    "FileTooLargeError",
    "validate_upload",
]
