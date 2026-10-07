"""Drawing File Validator and Format Classifier.

Implements strict two-tier validation (extension allowlist + binary magic signature)
and size enforcement for mechanical seal engineering drawings.
"""

from __future__ import annotations

import os
from pathlib import Path

MAX_DRAWING_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

VIEWABLE_IN_BROWSER = frozenset({"PDF", "PNG", "JPEG"})
ACCEPTED_DOWNLOAD_ONLY = frozenset({"TIFF", "DWG", "DXF", "STEP"})

ALLOWED_EXTENSIONS = frozenset({
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".dwg",
    ".dxf",
    ".step",
    ".stp",
})

REJECTED_EXTENSIONS = frozenset({
    ".exe", ".bat", ".cmd", ".sh", ".js", ".vbs", ".py",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".xlsm", ".docm", ".dotm", ".xltm",
})

MIME_TYPE_MAPPING = {
    "PDF": "application/pdf",
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "TIFF": "image/tiff",
    "DWG": "application/acad",
    "DXF": "application/dxf",
    "STEP": "application/step",
}


class DrawingValidationError(ValueError):
    """Base error for drawing validation failures."""


class DrawingFileTooLargeError(DrawingValidationError):
    """Raised when file exceeds MAX_DRAWING_FILE_SIZE_BYTES."""


class InvalidDrawingExtensionError(DrawingValidationError):
    """Raised when file extension is not in ALLOWED_EXTENSIONS or is forbidden."""


class DrawingSignatureMismatchError(DrawingValidationError):
    """Raised when binary header signature does not match expected file format."""


def _detect_format_signature(header: bytes) -> str | None:
    """Inspects initial byte stream to identify actual file format."""
    if header.startswith(b"%PDF-"):
        return "PDF"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        return "TIFF"
    if header.startswith(b"AC10") or header.startswith(b"AC"):
        return "DWG"
    if header.startswith(b"AutoCAD Binary DXF"):
        return "DXF"
    if b"SECTION" in header[:256] and b"HEADER" in header[:512]:
        return "DXF"
    if b"0\r\nSECTION" in header[:256] or b"0\nSECTION" in header[:256]:
        return "DXF"
    if b"ISO-10303-21" in header[:512].upper():
        return "STEP"
    return None


def _format_from_extension(ext: str) -> str:
    ext_lower = ext.lower()
    if ext_lower == ".pdf":
        return "PDF"
    if ext_lower == ".png":
        return "PNG"
    if ext_lower in (".jpg", ".jpeg"):
        return "JPEG"
    if ext_lower in (".tif", ".tiff"):
        return "TIFF"
    if ext_lower == ".dwg":
        return "DWG"
    if ext_lower == ".dxf":
        return "DXF"
    if ext_lower in (".step", ".stp"):
        return "STEP"
    return "UNKNOWN"


def validate_drawing_file(
    file_bytes: bytes,
    filename: str,
) -> dict[str, str | int]:
    """Validates file size, extension, and content signature.

    Returns dict with verified metadata:
        format: str ('PDF', 'DWG', etc.)
        content_type: str ('application/pdf', etc.)
        view_category: str ('VIEWABLE_IN_BROWSER' | 'ACCEPTED_DOWNLOAD_ONLY')
        file_size_bytes: int
        clean_extension: str
    """
    file_size = len(file_bytes)
    if file_size > MAX_DRAWING_FILE_SIZE_BYTES:
        raise DrawingFileTooLargeError(
            f"File size {file_size} bytes exceeds the {MAX_DRAWING_FILE_SIZE_BYTES}-byte limit (50 MB)"
        )
    if file_size == 0:
        raise DrawingValidationError("Uploaded file is empty (0 bytes)")

    ext = Path(filename).suffix.lower()
    if not ext or ext in REJECTED_EXTENSIONS or ext not in ALLOWED_EXTENSIONS:
        raise InvalidDrawingExtensionError(
            f"File extension {ext!r} is not allowed. Supported formats: {sorted(ALLOWED_EXTENSIONS)}"
        )

    expected_format = _format_from_extension(ext)
    detected_format = _detect_format_signature(file_bytes[:1024])

    if detected_format != expected_format:
        raise DrawingSignatureMismatchError(
            f"File extension {ext} (expected {expected_format}) does not match content signature ({detected_format or 'UNKNOWN'})"
        )

    view_category = (
        "VIEWABLE_IN_BROWSER"
        if detected_format in VIEWABLE_IN_BROWSER
        else "ACCEPTED_DOWNLOAD_ONLY"
    )

    return {
        "format": detected_format,
        "content_type": MIME_TYPE_MAPPING.get(detected_format, "application/octet-stream"),
        "view_category": view_category,
        "file_size_bytes": file_size,
        "clean_extension": ext,
    }


__all__ = [
    "MAX_DRAWING_FILE_SIZE_BYTES",
    "VIEWABLE_IN_BROWSER",
    "ACCEPTED_DOWNLOAD_ONLY",
    "ALLOWED_EXTENSIONS",
    "DrawingValidationError",
    "DrawingFileTooLargeError",
    "InvalidDrawingExtensionError",
    "DrawingSignatureMismatchError",
    "validate_drawing_file",
]

