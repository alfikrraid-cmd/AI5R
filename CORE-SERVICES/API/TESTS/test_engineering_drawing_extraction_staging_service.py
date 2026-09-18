"""MWO-LTSA-DRAWING-INPUT-R5B -- EngineeringDrawingExtractionStagingService
against a REAL, disposable, published-port Postgres. Same container/
bootstrap/truncate pattern as test_engineering_drawing_attribute_schema.py
(Drawing-R5A). NO external/paid AI call anywhere in this file -- a fake
DrawingExtractionProvider and a fake DrawingSourceBytesProvider stand in
for the real Claude/MinIO implementations.
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
for _path in (_CORE_SERVICES_DIR, _INGESTION_DIR, _AI_EXTRACTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner, bootstrap_schema  # noqa: E402
from API.engineering_drawing_extraction_staging_service import (  # noqa: E402
    DETECTED_DOCUMENT_TYPE,
    EngineeringDrawingExtractionStagingService,
    ExtractionFailed,
    FileUnavailable,
    UnsupportedMedia,
)
from drawing_extraction_models import (  # noqa: E402
    DocumentIdentity,
    DrawingExtractionResult,
    DrawingIdentityCandidates,
    IdentityFieldCandidate,
    RevisionCandidate,
)

_CONTAINER_NAME = "ai5r-test-drawing-extraction-staging-pg"
_USER = "ai5r"
_PASSWORD = "test-drawing-extraction-staging-password"
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


class FakeBytesProvider:
    def __init__(self, sources: dict[str, tuple[bytes, str]]):
        self._sources = sources

    def get_bytes(self, knowledge_source_id: str) -> tuple[bytes, str]:
        if knowledge_source_id not in self._sources:
            raise RuntimeError(f"no such source: {knowledge_source_id}")
        return self._sources[knowledge_source_id]


class FakeExtractionProvider:
    def __init__(self, result: DrawingExtractionResult | None = None, raise_error: Exception | None = None):
        self._result = result
        self._raise_error = raise_error
        self.calls: list[tuple[bytes, str]] = []

    def extract(self, file_bytes: bytes, mime_type: str) -> DrawingExtractionResult:
        self.calls.append((file_bytes, mime_type))
        if self._raise_error:
            raise self._raise_error
        return self._result


def _sample_result(mime_type: str = "application/pdf") -> DrawingExtractionResult:
    return DrawingExtractionResult(
        schema_version="drawing-extraction-v1",
        document_identity=DocumentIdentity(mime_type=mime_type),
        drawing_identity=DrawingIdentityCandidates(
            drawing_number=IdentityFieldCandidate(raw_value=None),
            title=IdentityFieldCandidate(raw_value="Test Drawing"),
            manufacturer=IdentityFieldCandidate(raw_value="John Crane"),
            drawing_type=IdentityFieldCandidate(),
        ),
        revision_candidate=RevisionCandidate(),
        references=(),
        attributes=(),
        bom_candidates=(),
        warnings=("DRAWING_NUMBER_NOT_FOUND",),
        ocr_text="sample",
        provider="claude:drawing-extraction-prompt-v1",
    )


@pytest.fixture(scope="module")
def pg_port():
    subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)
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
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], capture_output=True, text=True)


@pytest.fixture
def runner(pg_port):
    r = DatabaseRunner(
        DatabaseConfig(host="127.0.0.1", port=pg_port, user=_USER, password=_PASSWORD, database=_DATABASE)
    )
    r.execute_script(
        "TRUNCATE document_field_extraction, engineering_drawing_attribute, engineering_drawing_bom_line, "
        "engineering_drawing_link, engineering_drawing_revision_artifact, engineering_drawing_revision, "
        "engineering_drawing, knowledge_source_registry RESTART IDENTITY CASCADE;"
    )
    r.execute_script(
        "INSERT INTO knowledge_source_registry (knowledge_source_id, source_type, source_name) VALUES "
        "('KS-PDF', 'DRAWING', 'Test PDF'), ('KS-STEP', 'DRAWING', 'Test STEP'), "
        "('KS-MISSING-BYTES', 'DRAWING', 'Test Missing');"
    )
    return r


def _count(runner, sql):
    return int(runner.query_scalar(sql) or "0")


def test_staging_creates_candidate_row(runner):
    bytes_provider = FakeBytesProvider({"KS-PDF": (b"%PDF-1.4 fake", "application/pdf")})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    created = service.stage_extraction("KS-PDF")
    assert created["detected_document_type"] == DETECTED_DOCUMENT_TYPE
    assert created["source_document_id"] == "KS-PDF"
    assert created["status"] == "PENDING_REVIEW"
    assert created["extraction_provider"] == "claude:drawing-extraction-prompt-v1"


def test_idempotent_second_call_returns_same_row(runner):
    bytes_provider = FakeBytesProvider({"KS-PDF": (b"%PDF-1.4 fake", "application/pdf")})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    first = service.stage_extraction("KS-PDF")
    second = service.stage_extraction("KS-PDF")
    assert first["document_field_extraction_id"] == second["document_field_extraction_id"]
    assert len(extraction_provider.calls) == 1  # extraction only ran once
    assert _count(runner, f"SELECT COUNT(*) FROM document_field_extraction WHERE source_document_id = 'KS-PDF'") == 1


@pytest.mark.parametrize("mime_type", [
    "model/step", "application/step", "model/stl", "application/octet-stream",
])
def test_unsupported_cad_media_deferred_not_parsed(runner, mime_type):
    bytes_provider = FakeBytesProvider({"KS-STEP": (b"fake cad bytes", mime_type)})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    with pytest.raises(UnsupportedMedia):
        service.stage_extraction("KS-STEP")
    assert len(extraction_provider.calls) == 0  # never even attempted


def test_file_unavailable(runner):
    bytes_provider = FakeBytesProvider({})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    with pytest.raises(FileUnavailable):
        service.stage_extraction("KS-MISSING-BYTES")


def test_extraction_failed(runner):
    bytes_provider = FakeBytesProvider({"KS-PDF": (b"%PDF-1.4 fake", "application/pdf")})
    extraction_provider = FakeExtractionProvider(raise_error=RuntimeError("AI call failed"))
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    with pytest.raises(ExtractionFailed):
        service.stage_extraction("KS-PDF")
    assert _count(runner, "SELECT COUNT(*) FROM document_field_extraction") == 0


def test_no_canonical_drawing_writes(runner):
    bytes_provider = FakeBytesProvider({"KS-PDF": (b"%PDF-1.4 fake", "application/pdf")})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    service.stage_extraction("KS-PDF")

    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_revision_artifact") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_link") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_bom_line") == 0
    assert _count(runner, "SELECT COUNT(*) FROM engineering_drawing_attribute") == 0


def test_raw_extraction_preserved_immutably_in_extracted_fields(runner):
    bytes_provider = FakeBytesProvider({"KS-PDF": (b"%PDF-1.4 fake", "application/pdf")})
    extraction_provider = FakeExtractionProvider(result=_sample_result())
    service = EngineeringDrawingExtractionStagingService(runner, bytes_provider, extraction_provider)

    created = service.stage_extraction("KS-PDF")
    fetched = _json_extracted_fields(runner, created["document_field_extraction_id"])
    assert fetched["drawing_identity"]["title"]["raw_value"] == "Test Drawing"
    assert "DRAWING_NUMBER_NOT_FOUND" in fetched["warnings"]


def _json_extracted_fields(runner, candidate_id):
    import json as _json
    raw = runner.query_scalar(
        f"SELECT extracted_fields::text FROM document_field_extraction WHERE document_field_extraction_id = '{candidate_id}'"
    )
    return _json.loads(raw)
