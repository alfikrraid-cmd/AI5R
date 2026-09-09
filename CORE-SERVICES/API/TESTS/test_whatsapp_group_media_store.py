"""
Unit tests for WhatsAppGroupMediaStore, magic byte verification, and PDF validation.
"""
import time
import pytest
from pathlib import Path

from API.whatsapp_group_media_store import (
    WhatsAppGroupMediaStore,
    count_pdf_pages,
    format_file_size,
    sanitize_filename,
    validate_media_file,
    validate_pdf_structure,
)

SAMPLE_VALID_PDF_1_PAGE = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
    b"xref\n0 4\n"
    b"trailer\n<< /Root 1 0 R >>\n"
    b"%%EOF"
)

SAMPLE_VALID_PDF_50_PAGES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 50 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
    b"xref\n0 4\n"
    b"trailer\n<< /Root 1 0 R >>\n"
    b"%%EOF"
)

SAMPLE_OVERSIZED_PDF_51_PAGES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 51 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
    b"xref\n0 4\n"
    b"trailer\n<< /Root 1 0 R >>\n"
    b"%%EOF"
)

SAMPLE_CORRUPT_PDF_NO_EOF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
)

SAMPLE_CORRUPT_PDF_NO_PAGES = (
    b"%PDF-1.4\n"
    b"trailer\n<< >>\n%%EOF"
)

SAMPLE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50
SAMPLE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
SAMPLE_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 50


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(2 * 1024 * 1024) == "2.0 MB"


def test_sanitize_filename():
    assert sanitize_filename("../../../malicious.exe") == "malicious.exe"
    assert sanitize_filename("safe_report.pdf") == "safe_report.pdf"
    assert sanitize_filename("pump report (draft) #1!.pdf") == "pump_report__draft___1_.pdf"
    assert sanitize_filename("", fallback_ext=".pdf") == "evidence.pdf"


def test_validate_jpeg():
    valid, err = validate_media_file(SAMPLE_JPEG, "image/jpeg")
    assert valid is True
    assert err is None

    # image/jpg alias accepted
    valid, err = validate_media_file(SAMPLE_JPEG, "image/jpg")
    assert valid is True

    # Mismatch magic bytes
    valid, err = validate_media_file(SAMPLE_PNG, "image/jpeg")
    assert valid is False
    assert "JPEG" in err


def test_validate_png():
    valid, err = validate_media_file(SAMPLE_PNG, "image/png")
    assert valid is True
    assert err is None

    # Mismatch
    valid, err = validate_media_file(SAMPLE_JPEG, "image/png")
    assert valid is False
    assert "PNG" in err


def test_validate_webp():
    valid, err = validate_media_file(SAMPLE_WEBP, "image/webp")
    assert valid is True
    assert err is None

    # Mismatch
    valid, err = validate_media_file(SAMPLE_JPEG, "image/webp")
    assert valid is False
    assert "WEBP" in err


def test_validate_pdf_valid():
    valid, err = validate_media_file(SAMPLE_VALID_PDF_1_PAGE, "application/pdf")
    assert valid is True
    assert err is None

    valid, err = validate_media_file(SAMPLE_VALID_PDF_50_PAGES, "application/pdf")
    assert valid is True
    assert err is None


def test_validate_pdf_page_limit_50():
    valid, err = validate_media_file(SAMPLE_OVERSIZED_PDF_51_PAGES, "application/pdf")
    assert valid is False
    assert "melebihi batas maksimum 50 halaman" in err
    assert "51" in err


def test_validate_pdf_corrupt():
    valid, err = validate_media_file(SAMPLE_CORRUPT_PDF_NO_EOF, "application/pdf")
    assert valid is False
    assert "penanda akhir file" in err

    valid, err = validate_media_file(SAMPLE_CORRUPT_PDF_NO_PAGES, "application/pdf")
    assert valid is False
    assert "tidak memiliki halaman yang valid" in err


def test_validate_file_size_limit():
    huge_data = b"\xff\xd8\xff" + b"\x00" * (16 * 1024 * 1024)
    valid, err = validate_media_file(huge_data, "image/jpeg")
    assert valid is False
    assert "melebihi batas maksimum 15 MB" in err


def test_media_store_lifecycle(tmp_path):
    store = WhatsAppGroupMediaStore(spool_dir=tmp_path, ttl_seconds=2.0)

    # 1. Stage media
    rec = store.stage_media(
        sender_user_id="user-1",
        sender_hash="sender-hash-1",
        group_hash="group-hash-1",
        raw_bytes=SAMPLE_JPEG,
        mimetype="image/jpeg",
        filename="photo.jpg",
        pump_tag="211-P-16B",
        target_type="CONDITION_MONITORING_READING",
        target_record_code="CMONR-TEST001",
        category="PHOTO",
    )
    assert rec.filename == "photo.jpg"
    assert Path(rec.spool_path).is_file()
    assert rec.get_bytes() == SAMPLE_JPEG

    # 2. Get pending
    retrieved = store.get_pending(sender_user_id="user-1", group_hash="group-hash-1")
    assert retrieved is not None
    assert retrieved.confirmation_id == rec.confirmation_id

    # 3. Cross-user isolation: user-2 cannot retrieve user-1's pending media
    assert store.get_pending(sender_user_id="user-2", group_hash="group-hash-1") is None

    # 4. Cross-group isolation: group-2 cannot retrieve group-1's pending media
    assert store.get_pending(sender_user_id="user-1", group_hash="group-hash-2") is None

    # 5. Overwrite: staging new media deletes previous spool file
    old_spool = rec.spool_path
    rec2 = store.stage_media(
        sender_user_id="user-1",
        sender_hash="sender-hash-1",
        group_hash="group-hash-1",
        raw_bytes=SAMPLE_PNG,
        mimetype="image/png",
        filename="photo2.png",
        pump_tag="211-P-16B",
        target_type="CONDITION_MONITORING_READING",
        target_record_code="CMONR-TEST001",
        category="PHOTO",
    )
    assert not Path(old_spool).exists()
    assert Path(rec2.spool_path).exists()

    # 6. Discard
    discarded = store.discard_pending(sender_user_id="user-1", group_hash="group-hash-1")
    assert discarded is not None
    assert not Path(rec2.spool_path).exists()
    assert store.get_pending(sender_user_id="user-1", group_hash="group-hash-1") is None


def test_media_store_ttl_expiration(tmp_path):
    store = WhatsAppGroupMediaStore(spool_dir=tmp_path, ttl_seconds=0.1)
    rec = store.stage_media(
        sender_user_id="user-1",
        sender_hash="sender-hash-1",
        group_hash="group-hash-1",
        raw_bytes=SAMPLE_JPEG,
        mimetype="image/jpeg",
        filename="photo.jpg",
        pump_tag="211-P-16B",
        target_type="CONDITION_MONITORING_READING",
        target_record_code="CMONR-TEST001",
    )
    assert Path(rec.spool_path).exists()
    time.sleep(0.15)
    # After TTL expires, get_pending returns None and file is deleted
    assert store.get_pending("user-1", "group-hash-1") is None
    assert not Path(rec.spool_path).exists()
