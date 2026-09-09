"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- Temporary spool storage and media validation
for WhatsApp group media ingestion (images, PDFs).

Security rules:
1. Pure Python validation: no external binary or C-extension dependency.
2. Max file size: 15 MB (15 * 1024 * 1024 bytes).
3. Allowed MIME types: image/jpeg, image/jpg, image/png, image/webp, application/pdf.
4. Magic byte verification: declared MIME must match header bytes.
5. PDF checks: must begin with %PDF-, contain %%EOF, and have 1..50 pages.
   Corrupt PDFs or PDFs with >50 pages are rejected with safe messages.
6. Temporary spool files are stored in an isolated directory with synthetic
   names ({uuid}.bin) -- never user-controlled filesystem paths.
7. TTL = 900s (15 minutes). Pending state is bound strictly to (sender_user_id, group_hash).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_PDF_PAGES = 50
DEFAULT_TTL_SECONDS = 900.0  # 15 minutes

ALLOWED_MIME_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"}
)

_PUMP_TAG_PATTERN = re.compile(
    r"(?<![A-Za-z0-9/-])(\d+)\s*-?\s*P\s*-?\s*(\d+)\s*([A-Z]{1,3})(?![A-Za-z0-9/-])",
    re.IGNORECASE,
)


def normalize_pump_tag(raw: str) -> str | None:
    match = _PUMP_TAG_PATTERN.fullmatch((raw or "").strip())
    if not match:
        return None
    return f"{match.group(1)}-P-{match.group(2)}{match.group(3).upper()}"


def extract_pump_tag_candidates(text: str) -> tuple[str, ...]:
    """Extract explicit pump tags and normalize compact forms such as 211p16b."""
    return tuple(
        dict.fromkeys(
            f"{match.group(1)}-P-{match.group(2)}{match.group(3).upper()}"
            for match in _PUMP_TAG_PATTERN.finditer(text or "")
        )
    )


def sanitize_filename(name: str, fallback_ext: str = "") -> str:
    """Sanitize user-provided filename for safe display and metadata storage."""
    base = os.path.basename(name or "").strip()
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    clean = clean.strip("._")
    if not clean:
        clean = f"evidence{fallback_ext}"
    if len(clean) > 100:
        stem, ext = os.path.splitext(clean)
        clean = stem[: 100 - len(ext)] + ext
    return clean


def format_file_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def count_pdf_pages(data: bytes) -> int:
    """Pure-Python page counter for PDF byte streams without third-party libraries."""
    dict_pattern = re.compile(rb"<<([^>]*)>>", re.DOTALL)
    counts: list[int] = []
    for dict_body in dict_pattern.finditer(data):
        content = dict_body.group(1)
        if re.search(rb"/Type\s*/Pages\b", content):
            count_match = re.search(rb"/Count\s+(\d+)", content)
            if count_match:
                try:
                    counts.append(int(count_match.group(1)))
                except ValueError:
                    pass
    if counts:
        return max(counts)

    # Fallback: count individual page objects
    pages = re.findall(rb"/Type\s*/Page\b(?![sSLlMm])", data)
    if pages:
        return len(pages)

    return 0


def validate_pdf_structure(data: bytes) -> tuple[bool, int, str | None]:
    """Validate PDF header, trailer, and page count."""
    if not data.startswith(b"%PDF-"):
        return False, 0, "Isi file tidak memiliki header PDF yang valid."
    if b"%%EOF" not in data[-4096:] and b"%%EOF" not in data:
        return False, 0, "File PDF tidak lengkap atau rusak (tidak ditemukan penanda akhir file)."

    pages = count_pdf_pages(data)
    if pages <= 0:
        return False, 0, "File PDF rusak atau tidak memiliki halaman yang valid."
    if pages > MAX_PDF_PAGES:
        return (
            False,
            pages,
            f"Dokumen PDF melebihi batas maksimum {MAX_PDF_PAGES} halaman (terdeteksi {pages} halaman).",
        )

    return True, pages, None


def validate_media_file(data: bytes, declared_mimetype: str) -> tuple[bool, str | None]:
    """Verify size, declared MIME, magic bytes, and PDF page counts."""
    file_size = len(data)
    if file_size == 0:
        return False, "File media kosong."
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, f"Ukuran file ({format_file_size(file_size)}) melebihi batas maksimum 15 MB."

    norm_mime = declared_mimetype.lower().strip()
    if norm_mime == "image/jpg":
        norm_mime = "image/jpeg"

    if norm_mime not in ALLOWED_MIME_TYPES:
        return (
            False,
            f"Tipe konten '{declared_mimetype}' tidak didukung. Format yang didukung: JPG, PNG, WEBP, PDF.",
        )

    # Magic byte verification
    if norm_mime == "image/jpeg":
        if not data.startswith(b"\xff\xd8\xff"):
            return False, "Isi file tidak sesuai dengan format JPEG/JPG."
    elif norm_mime == "image/png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Isi file tidak sesuai dengan format PNG."
    elif norm_mime == "image/webp":
        if len(data) < 12 or not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
            return False, "Isi file tidak sesuai dengan format WEBP."
    elif norm_mime == "application/pdf":
        is_valid_pdf, _, pdf_err = validate_pdf_structure(data)
        if not is_valid_pdf:
            return False, pdf_err

    return True, None


@dataclass(slots=True)
class PendingMediaRecord:
    confirmation_id: str
    sender_user_id: str
    sender_hash: str
    group_hash: str
    mimetype: str
    filename: str
    spool_path: str
    file_size_bytes: int
    sha256: str
    pump_tag: str
    target_type: str
    target_record_code: str
    target_record_id: int | None
    target_record_date: str | None
    category: str
    created_at: float
    expires_at: float

    def get_bytes(self) -> bytes | None:
        try:
            with open(self.spool_path, "rb") as f:
                return f.read()
        except OSError:
            logger.warning("Failed to read pending media spool file %s", self.spool_path)
            return None


class WhatsAppGroupMediaStore:
    def __init__(
        self,
        spool_dir: str | Path | None = None,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        if spool_dir is None:
            spool_dir = os.getenv("TAP_GROUP_MEDIA_SPOOL_DIR", "auth_state/pending_media")
        self.spool_dir = Path(spool_dir)
        self.ttl_seconds = ttl_seconds
        self._pending: dict[tuple[str, str], PendingMediaRecord] = {}
        os.makedirs(self.spool_dir, exist_ok=True)

    def _delete_file_safely(self, path_str: str) -> None:
        try:
            p = Path(path_str)
            if p.is_file():
                p.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("Could not unlink spool file %s: %s", path_str, e)

    def cleanup_expired(self) -> int:
        now = time.time()
        expired_keys = [
            k for k, rec in self._pending.items() if now > rec.expires_at
        ]
        for k in expired_keys:
            rec = self._pending.pop(k, None)
            if rec:
                self._delete_file_safely(rec.spool_path)
        return len(expired_keys)

    def stage_media(
        self,
        *,
        sender_user_id: str,
        sender_hash: str,
        group_hash: str,
        raw_bytes: bytes,
        mimetype: str,
        filename: str,
        pump_tag: str,
        target_type: str,
        target_record_code: str,
        target_record_id: int | None = None,
        target_record_date: str | None = None,
        category: str = "OTHER",
    ) -> PendingMediaRecord:
        self.cleanup_expired()
        key = (sender_user_id, group_hash)
        old_rec = self._pending.pop(key, None)
        if old_rec:
            self._delete_file_safely(old_rec.spool_path)

        confirmation_id = uuid.uuid4().hex
        spool_path = str(self.spool_dir / f"{confirmation_id}.bin")
        with open(spool_path, "wb") as f:
            f.write(raw_bytes)

        now = time.time()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        norm_mime = mimetype.lower().strip()
        if norm_mime == "image/jpg":
            norm_mime = "image/jpeg"

        rec = PendingMediaRecord(
            confirmation_id=confirmation_id,
            sender_user_id=sender_user_id,
            sender_hash=sender_hash,
            group_hash=group_hash,
            mimetype=norm_mime,
            filename=sanitize_filename(filename),
            spool_path=spool_path,
            file_size_bytes=len(raw_bytes),
            sha256=sha256,
            pump_tag=pump_tag,
            target_type=target_type,
            target_record_code=target_record_code,
            target_record_id=target_record_id,
            target_record_date=target_record_date,
            category=category,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self._pending[key] = rec
        return rec

    def get_pending(self, sender_user_id: str, group_hash: str) -> PendingMediaRecord | None:
        self.cleanup_expired()
        key = (sender_user_id, group_hash)
        rec = self._pending.get(key)
        if rec is None:
            return None
        if time.time() > rec.expires_at:
            self._pending.pop(key, None)
            self._delete_file_safely(rec.spool_path)
            return None
        return rec

    def discard_pending(self, sender_user_id: str, group_hash: str) -> PendingMediaRecord | None:
        self.cleanup_expired()
        key = (sender_user_id, group_hash)
        rec = self._pending.pop(key, None)
        if rec:
            self._delete_file_safely(rec.spool_path)
        return rec


__all__ = [
    "MAX_FILE_SIZE_BYTES",
    "MAX_PDF_PAGES",
    "DEFAULT_TTL_SECONDS",
    "ALLOWED_MIME_TYPES",
    "PendingMediaRecord",
    "WhatsAppGroupMediaStore",
    "sanitize_filename",
    "format_file_size",
    "count_pdf_pages",
    "validate_pdf_structure",
    "validate_media_file",
    "normalize_pump_tag",
    "extract_pump_tag_candidates",
]
