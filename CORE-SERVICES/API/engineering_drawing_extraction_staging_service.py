"""MWO-LTSA-DRAWING-INPUT-R5B -- Engineering Drawing extraction staging
service. STAGING EVIDENCE ONLY: this service writes exactly one
document_field_extraction row per successful extraction and NOTHING
else -- no engineering_drawing/_revision/_revision_artifact/_link/
_bom_line/_attribute row, no asset_registry/seal_registry/
internal_component_master row, ever. Reuses document_field_extraction
verbatim (the SAME staging table historical_pm_cmon_staging_repository.py
already governs) rather than a second staging table, per that file's own
"do NOT build a second generic ingestion engine" instruction.

Depends on a DrawingSourceBytesProvider (PRODUCTS/LTSA-BRAIN/AI-EXTRACTION/
drawing_extraction_provider.py) and a DrawingExtractionProvider, both
injected -- this service never imports MinIO or the Anthropic SDK
directly (Section 20's own provider-independence requirement).
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
_AI_EXTRACTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "AI-EXTRACTION"
for _path in (_INGESTION_DIR, _AI_EXTRACTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402
from drawing_extraction_models import SCHEMA_VERSION, SUPPORTED_MIME_TYPES, DrawingExtractionResult  # noqa: E402
from drawing_extraction_provider import DrawingExtractionProvider, DrawingSourceBytesProvider  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

DETECTED_DOCUMENT_TYPE = "ENGINEERING_DRAWING_CANDIDATE"

_SELECT_COLUMNS = (
    "document_field_extraction_id, source_document_id, source_document_type, "
    "detected_document_type, detected_document_type_confidence, extraction_provider, "
    "ocr_text, extracted_fields, reviewed_fields, status, pump_tag_number, seal_code, "
    "source_page, reviewed_by, reviewed_at, created_at, updated_at"
)

_MIME_TO_SOURCE_DOCUMENT_TYPE = {
    "application/pdf": "PDF",
    "image/jpeg": "MEDIA",
    "image/jpg": "MEDIA",
    "image/png": "MEDIA",
    "image/webp": "MEDIA",
}


class UnsupportedMedia(Exception):
    """mime_type is not one of drawing_extraction_models.SUPPORTED_MIME_TYPES
    (e.g. STEP/STL/FCStd/GLB/DXF/DWG) -- R5B never attempts CAD parsing;
    these formats are deferred, not rejected-as-broken."""


class FileUnavailable(Exception):
    """The injected DrawingSourceBytesProvider could not retrieve bytes
    for the given knowledge_source_id."""


class ExtractionFailed(Exception):
    """The extraction provider itself raised (e.g. the AI call failed)."""


class InvalidExtractionPayload(Exception):
    """The extraction provider returned a payload that could not be
    parsed into DrawingExtractionResult's own required shape."""


class EngineeringDrawingExtractionStagingService:
    def __init__(
        self,
        runner: "DatabaseRunner",
        bytes_provider: DrawingSourceBytesProvider,
        extraction_provider: DrawingExtractionProvider,
    ) -> None:
        self._runner = runner
        self._bytes_provider = bytes_provider
        self._extraction_provider = extraction_provider

    def _find_existing_candidate(self, knowledge_source_id: str) -> dict | None:
        # R5B Section 17 -- application-layer idempotency, mirroring the
        # only mechanism this schema already has (a plain, non-unique
        # index on (source_document_id, source_document_type) plus
        # historical_pm_cmon_staging_repository.py's own list_for_source()
        # pattern). DISCLOSED GAP: no DB-level uniqueness constraint
        # prevents a concurrent duplicate insert -- see this MWO's own
        # R5B_SCHEMA_GAP report; not solved here with a migration, per
        # Section 24's own "no migration unless unavoidable" instruction,
        # and never solved with a destructive overwrite.
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE source_document_id = {_sql(knowledge_source_id)} "
            f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)} "
            "AND status <> 'REJECTED' "
            "ORDER BY created_at LIMIT 1",
            self._runner,
        )
        return rows[0] if rows else None

    def stage_extraction(self, knowledge_source_id: str) -> dict:
        existing = self._find_existing_candidate(knowledge_source_id)
        if existing is not None:
            return existing

        try:
            file_bytes, mime_type = self._bytes_provider.get_bytes(knowledge_source_id)
        except Exception as exc:  # noqa: BLE001
            raise FileUnavailable(f"{knowledge_source_id}: {exc}") from exc

        if mime_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedMedia(
                f"{mime_type!r} is not automatically extractable in R5B "
                f"(supported: {SUPPORTED_MIME_TYPES}); the file may still be "
                "stored/classified as a Drawing artifact, just not parsed"
            )

        try:
            result = self._extraction_provider.extract(file_bytes, mime_type)
        except (UnsupportedMedia, FileUnavailable):
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExtractionFailed(f"{knowledge_source_id}: {exc}") from exc

        if not isinstance(result, DrawingExtractionResult):
            raise InvalidExtractionPayload(
                f"extraction provider returned {type(result).__name__}, expected DrawingExtractionResult"
            )

        candidate_id = f"DFE-{uuid.uuid4().hex[:16].upper()}"
        source_document_type = _MIME_TO_SOURCE_DOCUMENT_TYPE.get(mime_type, "MEDIA")
        payload = result.to_dict()
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO document_field_extraction "
                "(document_field_extraction_id, source_document_id, source_document_type, "
                "detected_document_type, extraction_provider, ocr_text, extracted_fields, status) "
                f"VALUES ({_sql(candidate_id)}, {_sql(knowledge_source_id)}, {_sql(source_document_type)}, "
                f"{_sql(DETECTED_DOCUMENT_TYPE)}, {_sql(result.provider)}, {_sql(result.ocr_text)}, "
                f"{_sql(json.dumps(payload))}::jsonb, 'PENDING_REVIEW') "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def list_for_source(self, knowledge_source_id: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE source_document_id = {_sql(knowledge_source_id)} "
            f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)} "
            "ORDER BY created_at",
            self._runner,
        )


__all__ = [
    "EngineeringDrawingExtractionStagingService",
    "DETECTED_DOCUMENT_TYPE",
    "UnsupportedMedia",
    "FileUnavailable",
    "ExtractionFailed",
    "InvalidExtractionPayload",
]
