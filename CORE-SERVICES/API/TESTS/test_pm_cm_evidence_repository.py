"""MWO-LTSA-PM-CM-INTAKE-001 -- PMCMEvidenceRepository tests: upload
validation (Phase 22) and SQL shape."""

import json
import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pm_cm_evidence_repository import (  # noqa: E402
    FileTooLargeError,
    PMCMEvidenceRepository,
    UnsupportedContentTypeError,
    validate_upload,
)


class FakeRunner:
    def __init__(self, scalar_response: str = "[]"):
        self.scalar_calls: list[str] = []
        self.scalar_response = scalar_response

    def query_scalar(self, sql: str) -> str:
        self.scalar_calls.append(sql)
        return self.scalar_response


def test_validate_upload_accepts_the_real_allowed_types():
    for content_type in ("image/jpeg", "image/png", "application/pdf"):
        validate_upload(content_type=content_type, file_size_bytes=1024)  # does not raise


def test_validate_upload_rejects_an_unlisted_content_type():
    with pytest.raises(UnsupportedContentTypeError):
        validate_upload(content_type="application/x-msdownload", file_size_bytes=1024)


def test_validate_upload_rejects_an_oversized_file():
    with pytest.raises(FileTooLargeError):
        validate_upload(content_type="image/jpeg", file_size_bytes=100 * 1024 * 1024)


def test_create_rejects_an_unsupported_content_type_before_any_sql_runs():
    runner = FakeRunner()
    repo = PMCMEvidenceRepository(runner)

    with pytest.raises(UnsupportedContentTypeError):
        repo.create(
            record_type="PM_OCCURRENCE", record_code="PMOCC-1", file_name="malware.exe",
            content_type="application/x-msdownload", file_bytes=b"fake", category=None,
            source="MANUAL", uploaded_by="actor-1",
        )

    assert runner.scalar_calls == []  # never reaches SQL


def test_create_never_wraps_a_bare_insert_in_a_select_from_subquery():
    runner = FakeRunner(scalar_response=json.dumps([{"evidence_id": "uuid-1"}]))
    repo = PMCMEvidenceRepository(runner)

    repo.create(
        record_type="PM_OCCURRENCE", record_code="PMOCC-1", file_name="seal_photo.jpg",
        content_type="image/jpeg", file_bytes=b"\xff\xd8\xff\x00", category="PHOTO",
        source="MANUAL", uploaded_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "FROM (INSERT" not in sql
    assert sql.strip().upper().startswith("WITH")
    assert "INSERT INTO pm_cm_evidence" in sql


def test_create_stores_bytes_as_a_bytea_hex_literal_never_as_base64_text():
    runner = FakeRunner(scalar_response=json.dumps([{"evidence_id": "uuid-1"}]))
    repo = PMCMEvidenceRepository(runner)

    repo.create(
        record_type="CONDITION_MONITORING_READING", record_code="CMONR-1", file_name="reading.pdf",
        content_type="application/pdf", file_bytes=b"\x25\x50\x44\x46", category="REPORT",
        source="MANUAL", uploaded_by="actor-1",
    )

    sql = runner.scalar_calls[0]
    assert "'\\x25504446'::bytea" in sql


def test_list_for_record_scopes_by_both_record_type_and_record_code():
    runner = FakeRunner(scalar_response="[]")
    repo = PMCMEvidenceRepository(runner)

    repo.list_for_record("PM_OCCURRENCE", "PMOCC-1")

    sql = runner.scalar_calls[0]
    assert "record_type = 'PM_OCCURRENCE'" in sql
    assert "record_code = 'PMOCC-1'" in sql


def test_get_file_data_never_leaks_bytes_into_list_or_create_responses():
    # file_data is deliberately absent from _SELECT_COLUMNS -- create()/
    # list_for_record() responses never carry the raw bytes, only
    # get_file_data() (a single, explicit download path) does.
    from API.pm_cm_evidence_repository import _SELECT_COLUMNS

    assert "file_data" not in _SELECT_COLUMNS
