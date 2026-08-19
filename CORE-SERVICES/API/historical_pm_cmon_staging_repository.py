"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- staging repository for
historical PM/Condition Monitoring candidates extracted from monthly
"Laporan PM, CM & Pemasangan Seal" reports.

Reuses document_field_extraction verbatim (the SAME AI-extraction/human-
review staging table MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 already
built and installation_review_service.py already governs) rather than a
second staging table -- per this MWO's own "Do NOT build a second generic
ingestion engine" instruction. Three new detected_document_type values
(migration 015) keep the PM/CMON/Finding domains distinct at the staging
layer too, mirroring the same separation pm_occurrence/condition_
monitoring_reading already enforce downstream: HISTORICAL_PM_OCCURRENCE_
CANDIDATE, HISTORICAL_CMON_READING_CANDIDATE, and
HISTORICAL_FINDING_CANDIDATE (a Finding row is staged on its own, never
auto-merged into a CMON candidate's `finding` field at extraction time --
see migration 015's own comment: every real pump tag has multiple dated
CM readings per monthly report, so which specific reading a finding
belongs to cannot be safely inferred; a human reviewer attaches it
explicitly). Never HISTORICAL_CM_REPORT_* -- this pipeline never writes
cm_report (Corrective Maintenance), per this MWO's own Semantic Freeze.

extraction_provider is honestly 'deterministic_workbook_table_parser' (not
'claude', the column's own default) -- no AI/document-intelligence service
is used anywhere in this pipeline; every extracted value comes from a
plain, deterministic openpyxl cell read of the source workbook. Per
Phase 20's own rule, AI is never authoritative here because AI is not
used at all.

status follows installation_review_service.py's own real state machine
(PENDING_REVIEW -> REVIEWED -> SAVED, or -> REJECTED) unmodified --
reused via validate_status_transition, not reimplemented.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .installation_review_service import validate_status_transition  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

PM_OCCURRENCE_CANDIDATE = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
CMON_READING_CANDIDATE = "HISTORICAL_CMON_READING_CANDIDATE"
FINDING_CANDIDATE = "HISTORICAL_FINDING_CANDIDATE"
EXTRACTION_PROVIDER = "deterministic_workbook_table_parser"

_SELECT_COLUMNS = (
    "document_field_extraction_id, source_document_id, source_document_type, "
    "detected_document_type, detected_document_type_confidence, extraction_provider, "
    "ocr_text, extracted_fields, reviewed_fields, status, pump_tag_number, seal_code, "
    "source_page, reviewed_by, reviewed_at, created_at, updated_at"
)


class InvalidStatusTransitionError(ValueError):
    pass


class HistoricalPMCMONStagingRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def create_candidate(
        self,
        *,
        source_document_id: str,
        detected_document_type: str,
        extracted_fields: dict,
        pump_tag_number: str | None = None,
        source_page: int | None = None,
    ) -> dict:
        candidate_id = f"DFE-{uuid.uuid4().hex[:16].upper()}"
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO document_field_extraction "
                "(document_field_extraction_id, source_document_id, source_document_type, "
                "detected_document_type, extraction_provider, extracted_fields, status, "
                "pump_tag_number, source_page) VALUES "
                f"({_sql(candidate_id)}, {_sql(source_document_id)}, 'PDF', "
                f"{_sql(detected_document_type)}, {_sql(EXTRACTION_PROVIDER)}, "
                f"{_sql(json.dumps(extracted_fields))}::jsonb, 'PENDING_REVIEW', "
                f"{_sql(pump_tag_number)}, {_sql(source_page)}) "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
            )
            or "[]"
        )
        return rows[0]

    def find_by_id(self, candidate_id: str) -> dict | None:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE document_field_extraction_id = {_sql(candidate_id)}",
            self._runner,
        )
        return rows[0] if rows else None

    def list_pending(self, detected_document_type: str | None = None) -> list[dict]:
        where = "status = 'PENDING_REVIEW'"
        if detected_document_type:
            where += f" AND detected_document_type = {_sql(detected_document_type)}"
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction WHERE {where} "
            "ORDER BY created_at ASC",
            self._runner,
        )

    def list_for_source(self, source_document_id: str) -> list[dict]:
        return _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE source_document_id = {_sql(source_document_id)} "
            "ORDER BY source_page ASC NULLS LAST, created_at ASC",
            self._runner,
        )

    def apply_review(
        self,
        candidate_id: str,
        *,
        reviewed_fields: dict,
        reviewed_by: str,
        next_status: str = "REVIEWED",
        pump_tag_number: str | None = None,
    ) -> dict | None:
        """Applies a human reviewer's correction. `reviewed_fields` is
        stored SEPARATELY from `extracted_fields` -- the original
        extraction is never overwritten (Phase 13's own explicit
        requirement: SOURCE-EXTRACTED VALUE vs HUMAN-CORRECTED VALUE,
        both retained)."""
        current = self.find_by_id(candidate_id)
        if current is None:
            return None
        if not validate_status_transition(current["status"], next_status):
            raise InvalidStatusTransitionError(
                f"cannot transition {current['status']!r} -> {next_status!r}"
            )

        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                f"reviewed_fields = {_sql(json.dumps(reviewed_fields))}::jsonb, "
                f"status = {_sql(next_status)}, "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), "
                f"pump_tag_number = COALESCE({_sql(pump_tag_number)}, pump_tag_number), "
                f"updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def reject(self, candidate_id: str, *, reviewed_by: str) -> dict | None:
        current = self.find_by_id(candidate_id)
        if current is None:
            return None
        if not validate_status_transition(current["status"], "REJECTED"):
            raise InvalidStatusTransitionError(f"cannot reject from {current['status']!r}")
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                "status = 'REJECTED', "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        return rows[0] if rows else None

    def mark_saved(self, candidate_id: str) -> None:
        self._runner.execute_script(
            "UPDATE document_field_extraction SET status = 'SAVED', updated_at = NOW() "
            f"WHERE document_field_extraction_id = {_sql(candidate_id)};"
        )


__all__ = [
    "HistoricalPMCMONStagingRepository",
    "InvalidStatusTransitionError",
    "PM_OCCURRENCE_CANDIDATE",
    "CMON_READING_CANDIDATE",
    "FINDING_CANDIDATE",
    "EXTRACTION_PROVIDER",
]
