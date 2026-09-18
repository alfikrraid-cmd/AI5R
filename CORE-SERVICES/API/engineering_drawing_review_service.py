"""MWO-LTSA-DRAWING-INPUT-R5C / R5C.1 -- Engineering Drawing human review
persistence. Writes ONLY to document_field_extraction.reviewed_fields/
status/reviewed_by/reviewed_at -- extracted_fields (RAW AUTHORITY) is
never mutated. CANONICAL WRITES=0: this service never reads or writes
engineering_drawing/_revision/_revision_artifact/_link/_bom_line/
_attribute, nor asset_registry/seal_registry/internal_component_master.
Promotion (turning a REVIEWED candidate into those canonical rows) is
Drawing-R5D's own, separate, later concern.

Same direct-Postgres, _json_query/_sql convention as
engineering_drawing_extraction_staging_service.py (R5B). All actual
review DECISIONS (what reviewed_fields should contain, whether a status
transition is currently allowed) are delegated to
engineering_drawing_review_contract.py's own pure functions -- this file
only fetches the current row, calls the contract, and persists the
result.

R5C.1 concurrency hardening: every write here is guarded by an
optimistic-concurrency precondition on the row's own `updated_at` value
as last read by THIS call -- no schema change, no new version column
(none was added; see this MWO's own REVIEW_CONCURRENCY_GAP disclosure).
If another reviewer's write landed on the same row between this call's
read and its write, the UPDATE affects zero rows and StaleReviewWrite is
raised instead of silently overwriting the other reviewer's change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .engineering_drawing_extraction_staging_service import DETECTED_DOCUMENT_TYPE  # noqa: E402
from .engineering_drawing_review_contract import (  # noqa: E402
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_REVIEWED,
    STATUS_SAVED,
    InvalidReviewAction,
    InvalidReviewTransition,
    apply_artifact_review,
    apply_attribute_review,
    apply_bom_review,
    apply_identity_field_review,
    apply_reference_review,
    apply_revision_review,
    can_finalize_review,
    is_promotion_eligible,
    validate_status_transition,
)

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner

_SELECT_COLUMNS = (
    "document_field_extraction_id, source_document_id, source_document_type, "
    "detected_document_type, detected_document_type_confidence, extraction_provider, "
    "ocr_text, extracted_fields, reviewed_fields, status, pump_tag_number, seal_code, "
    "source_page, reviewed_by, reviewed_at, created_at, updated_at"
)

_REVIEWABLE_STATUSES = frozenset({STATUS_PENDING_REVIEW, STATUS_REVIEWED})


class CandidateNotFound(Exception):
    """candidate_id does not exist, or is not an ENGINEERING_DRAWING_CANDIDATE."""


class CandidateNotReviewable(Exception):
    """status is SAVED or REJECTED -- both terminal (installation_review_
    service.py's own Hard Rule 9/10 precedent: once saved or rejected,
    nothing further happens to that draft)."""


class StaleReviewWrite(Exception):
    """R5C.1 -- another write landed on this candidate between this
    call's own read and its write attempt (detected via the row's
    updated_at no longer matching what this call last read). The
    attempted write was NOT applied -- re-fetch the candidate and retry
    with the reviewer's own intent reapplied against the current state,
    never blindly resubmit the stale computation."""


class EngineeringDrawingReviewService:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def get_candidate(self, candidate_id: str) -> dict:
        rows = _json_query(
            f"SELECT {_SELECT_COLUMNS} FROM document_field_extraction "
            f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
            f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)}",
            self._runner,
        )
        if not rows:
            raise CandidateNotFound(candidate_id)
        return rows[0]

    def promotion_eligible(self, candidate_id: str) -> bool:
        """Convenience read-only check (R5C.1 Section 5) -- Drawing-R5D's
        own preflight may call this directly instead of re-implementing
        is_promotion_eligible's own import/logic."""
        candidate = self.get_candidate(candidate_id)
        return is_promotion_eligible(candidate.get("reviewed_fields") or {})

    def _require_reviewable(self, candidate: dict) -> None:
        if candidate["status"] not in _REVIEWABLE_STATUSES:
            raise CandidateNotReviewable(
                f"{candidate['document_field_extraction_id']} has terminal status {candidate['status']!r}"
            )

    def _row_exists(self, candidate_id: str) -> bool:
        rows = _json_query(
            f"SELECT 1 AS ok FROM document_field_extraction WHERE document_field_extraction_id = {_sql(candidate_id)} "
            f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)}",
            self._runner,
        )
        return bool(rows)

    def _persist_reviewed_fields(self, candidate_id: str, reviewed_fields: dict, *, reviewed_by: str, expected_updated_at: str) -> dict:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                f"reviewed_fields = {_sql(json.dumps(reviewed_fields))}::jsonb, "
                f"reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)} "
                f"AND updated_at = {_sql(expected_updated_at)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        if not rows:
            if self._row_exists(candidate_id):
                raise StaleReviewWrite(
                    f"{candidate_id} was modified by another write since it was last read; re-fetch and retry"
                )
            raise CandidateNotFound(candidate_id)
        return rows[0]

    # ---- identity ----

    def review_identity_field(self, candidate_id: str, *, field_name: str, action: str, corrected_raw_value: str | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_identity_field_review(
            candidate.get("reviewed_fields") or {}, field_name=field_name, action=action, corrected_raw_value=corrected_raw_value,
        )
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def review_revision(self, candidate_id: str, *, action: str, corrected_revision: str | None = None, corrected_revision_date: str | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_revision_review(
            candidate.get("reviewed_fields") or {}, action=action, corrected_revision=corrected_revision, corrected_revision_date=corrected_revision_date,
        )
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def review_artifact(self, candidate_id: str, *, action: str, extracted_class: str | None = None, corrected_class: str | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_artifact_review(
            candidate.get("reviewed_fields") or {}, action=action, extracted_class=extracted_class,
            corrected_class=corrected_class, knowledge_source_id=candidate["source_document_id"],
        )
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def review_reference(self, candidate_id: str, *, index: int, action: str, corrected_value: dict | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_reference_review(candidate.get("reviewed_fields") or {}, index=index, action=action, corrected_value=corrected_value)
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def review_attribute(self, candidate_id: str, *, index: int, action: str, corrected_value: dict | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_attribute_review(candidate.get("reviewed_fields") or {}, index=index, action=action, corrected_value=corrected_value)
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def review_bom_line(self, candidate_id: str, *, index: int, action: str, corrected_value: dict | None = None, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        self._require_reviewable(candidate)
        new_reviewed_fields = apply_bom_review(candidate.get("reviewed_fields") or {}, index=index, action=action, corrected_value=corrected_value)
        return self._persist_reviewed_fields(candidate_id, new_reviewed_fields, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    # ---- status transitions ----

    def finalize_review(self, candidate_id: str, *, reviewed_by: str) -> dict:
        candidate = self.get_candidate(candidate_id)
        reviewed_fields = candidate.get("reviewed_fields") or {}
        if not can_finalize_review(candidate["status"], reviewed_fields):
            raise InvalidReviewTransition(
                f"{candidate_id} cannot be finalized to {STATUS_REVIEWED!r} from status "
                f"{candidate['status']!r} with the current reviewed_fields (identity/artifact review "
                "incomplete, or transition not permitted)"
            )
        return self._transition_status(candidate_id, STATUS_REVIEWED, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def reject_candidate(self, candidate_id: str, *, reviewed_by: str) -> dict:
        # Whole-candidate rejection -- terminal, distinct from
        # review_artifact(..., action="REJECT") which only marks the
        # artifact sub-field within reviewed_fields and never touches
        # this row's own status (R5C.1 Section 9's own explicit rule).
        candidate = self.get_candidate(candidate_id)
        if not validate_status_transition(candidate["status"], STATUS_REJECTED):
            raise InvalidReviewTransition(f"{candidate_id} cannot transition from {candidate['status']!r} to {STATUS_REJECTED!r}")
        return self._transition_status(candidate_id, STATUS_REJECTED, reviewed_by=reviewed_by, expected_updated_at=candidate["updated_at"])

    def _transition_status(self, candidate_id: str, new_status: str, *, reviewed_by: str, expected_updated_at: str) -> dict:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE document_field_extraction SET "
                f"status = {_sql(new_status)}, reviewed_by = {_sql(reviewed_by)}, reviewed_at = NOW(), updated_at = NOW() "
                f"WHERE document_field_extraction_id = {_sql(candidate_id)} "
                f"AND detected_document_type = {_sql(DETECTED_DOCUMENT_TYPE)} "
                f"AND updated_at = {_sql(expected_updated_at)} "
                f"RETURNING {_SELECT_COLUMNS}"
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
            )
            or "[]"
        )
        if not rows:
            if self._row_exists(candidate_id):
                raise StaleReviewWrite(
                    f"{candidate_id} was modified by another write since it was last read; re-fetch and retry"
                )
            raise CandidateNotFound(candidate_id)
        return rows[0]


__all__ = [
    "EngineeringDrawingReviewService",
    "CandidateNotFound",
    "CandidateNotReviewable",
    "StaleReviewWrite",
    "InvalidReviewAction",
    "InvalidReviewTransition",
]
