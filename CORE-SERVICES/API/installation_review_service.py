"""
MWO-LTSA-INSTALLATION-REPORT-INGESTION-001 -- Installation Report review
contract: pump/seal identity matching and the document_field_extraction ->
installation_report human-approval gate.

No SQL, no API, no gateway changes. Pure functions operating on
already-fetched rows (dicts), the same "no gateway calls of its own"
discipline equipment_timeline_service.py already establishes -- a caller
(future API route or n8n workflow) is responsible for fetching candidate
pump/seal rows and persisting the result; this module only decides.

Reuses the existing, already-committed document_field_extraction contract
verbatim (status: PENDING_REVIEW/REVIEWED/SAVED/REJECTED; pump_tag_number/
seal_code as the match outcome columns) rather than inventing a parallel
review table or a second matching engine. "NEEDS_REVIEW" (the MWO's own
vocabulary) is PENDING_REVIEW never auto-advancing past it -- there is
deliberately no separate NEEDS_REVIEW status string; a low-confidence or
ambiguous/absent match simply leaves status at its PENDING_REVIEW default
forever, until a human reviewer resolves it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MatchOutcome = Literal["MATCHED", "AMBIGUOUS", "NOT_FOUND"]

# Never auto-promote a match the model itself is not confident about --
# Phase 5's "Low-confidence identity match -> NEEDS_REVIEW" rule.
DEFAULT_CONFIDENCE_THRESHOLD = 0.85

# document_field_extraction.status's own CHECK constraint (CANONICAL_SCHEMA.sql,
# migration 010) -- kept as a single source of truth here so a caller/test
# never hand-types the four strings.
STATUS_PENDING_REVIEW = "PENDING_REVIEW"
STATUS_REVIEWED = "REVIEWED"
STATUS_SAVED = "SAVED"
STATUS_REJECTED = "REJECTED"

# The only transitions this contract permits. REJECTED and SAVED are both
# terminal (Hard Rule 9/10: no automatic AI-to-canonical write, human
# review required before canonical mutation -- once saved or rejected,
# nothing further happens to that draft).
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_PENDING_REVIEW: frozenset({STATUS_REVIEWED, STATUS_REJECTED}),
    STATUS_REVIEWED: frozenset({STATUS_SAVED, STATUS_REJECTED, STATUS_PENDING_REVIEW}),
    STATUS_SAVED: frozenset(),
    STATUS_REJECTED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class MatchResult:
    outcome: MatchOutcome
    matched_id: str | None = None
    candidate_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_review(self) -> bool:
        return self.outcome != "MATCHED"


def match_pump(plant_equip_no: str | None, candidate_pumps: list[dict[str, Any]]) -> MatchResult:
    """candidate_pumps: rows already filtered by the caller (e.g. an exact or
    fuzzy tag_number lookup against ltsa_pumps) -- this function only
    classifies the result count, it never queries anything itself.

    Phase 5: no pump match -> NEEDS_REVIEW; multiple pump matches ->
    NEEDS_REVIEW. An unresolvable identity (blank plant_equip_no) is
    treated the same as NOT_FOUND -- never guessed.
    """
    if not plant_equip_no or not plant_equip_no.strip():
        return MatchResult(outcome="NOT_FOUND")
    if not candidate_pumps:
        return MatchResult(outcome="NOT_FOUND")
    if len(candidate_pumps) > 1:
        return MatchResult(
            outcome="AMBIGUOUS",
            candidate_ids=tuple(row["tag_number"] for row in candidate_pumps),
        )
    return MatchResult(outcome="MATCHED", matched_id=candidate_pumps[0]["tag_number"])


def match_seal(seal_code_hint: str | None, candidate_seals: list[dict[str, Any]]) -> MatchResult:
    """Mirrors match_pump exactly. A report with no seal_registry identifier
    at all (only descriptive text, e.g. sampleInstallations.js's real
    seed row) is NOT_FOUND -- that is a legitimate, historically-evidenced
    outcome (Phase 2: descriptive fields are preserved regardless), not an
    error; it simply means installation_report.seal_code stays NULL and
    the report is not blocked on it alone.
    """
    if not seal_code_hint or not seal_code_hint.strip():
        return MatchResult(outcome="NOT_FOUND")
    if not candidate_seals:
        return MatchResult(outcome="NOT_FOUND")
    if len(candidate_seals) > 1:
        return MatchResult(
            outcome="AMBIGUOUS",
            candidate_ids=tuple(row["seal_code"] for row in candidate_seals),
        )
    return MatchResult(outcome="MATCHED", matched_id=candidate_seals[0]["seal_code"])


def resolve_pump_review_gate(
    pump_match: MatchResult,
    *,
    detected_document_type_confidence: float | None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    """Returns True if the draft must stay gated at PENDING_REVIEW (never
    auto-advance) because of the pump identity alone. Critical identity
    fields must never be silently guessed (Phase 5) -- an AMBIGUOUS or
    NOT_FOUND pump match, or a low-confidence overall extraction, both
    force review regardless of anything else on the report.
    """
    if pump_match.needs_review:
        return True
    if detected_document_type_confidence is None:
        return True
    return detected_document_type_confidence < confidence_threshold


def validate_status_transition(current_status: str, next_status: str) -> bool:
    return next_status in _ALLOWED_TRANSITIONS.get(current_status, frozenset())


class InvalidReviewTransition(ValueError):
    pass


class UnresolvedIdentityError(ValueError):
    pass


# document_field_extraction column name -> installation_report column name,
# for the subset of fields document_field_extraction actually carries.
# Deliberately partial: only fields a real extraction can plausibly
# populate today (report/pump/seal identity + provenance). Every other
# installation_report column (BOM, observations, signatures, ...) is
# reviewer-authored/corrected in `reviewed_fields` under its own
# installation_report column name already -- this map does not invent new
# field names, it only documents the ones extraction can autofill.
EXTRACTED_TO_INSTALLATION_REPORT_FIELDS: dict[str, str] = {
    "reportNo": "report_no",
    "reportDate": "report_date",
    "customer": "customer",
    "plant": "plant",
    "unit": "unit",
    "plantEquipNo": "plant_equip_no",
    "equipmentMfr": "equipment_mfr",
    "sealType": "seal_type",
    "sealManufacture": "seal_manufacture",
    "sealArrangement": "seal_arrangement",
    "sourceDocumentName": "source_document_name",
}


def build_installation_report_row(
    extraction: dict[str, Any],
    *,
    installation_code: str,
) -> dict[str, Any]:
    """The one and only promotion path from a draft to a canonical
    installation_report row (Hard Rule 9/10: AI extraction never mutates
    canonical records directly; this function is only ever called by a
    caller that has already verified status == REVIEWED and pump/seal
    identity is resolved -- it re-verifies both itself rather than trusting
    the caller, since this is the sole gate before a real INSERT).

    reviewed_fields (human-corrected) always wins over extracted_fields
    (AI-guessed) for any field present in both -- the human review is the
    entire point of the REVIEWED status.
    """
    if extraction.get("status") != STATUS_REVIEWED:
        raise InvalidReviewTransition(
            f"cannot promote a document_field_extraction row with status "
            f"{extraction.get('status')!r}; only {STATUS_REVIEWED!r} rows may be saved"
        )
    if not extraction.get("pump_tag_number"):
        raise UnresolvedIdentityError("cannot save an installation_report row with no matched pump_tag_number")

    reviewed_fields = extraction.get("reviewed_fields") or {}
    extracted_fields = extraction.get("extracted_fields") or {}

    row: dict[str, Any] = {"installation_code": installation_code}
    for extracted_key, column in EXTRACTED_TO_INSTALLATION_REPORT_FIELDS.items():
        if extracted_key in reviewed_fields:
            row[column] = reviewed_fields[extracted_key]
        elif extracted_key in extracted_fields:
            value = extracted_fields[extracted_key]
            # AI-EXTRACTION/models.py's FieldValue(value, confidence) shape --
            # extracted_fields stores {value, confidence} per field;
            # reviewed_fields stores the plain, human-confirmed value.
            row[column] = value["value"] if isinstance(value, dict) and "value" in value else value

    row["plant_equip_no"] = extraction["pump_tag_number"]
    if extraction.get("seal_code"):
        row["seal_code"] = extraction["seal_code"]

    return row
