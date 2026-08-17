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


# document_field_extraction key (camelCase, matching sampleInstallations.js/
# AI-EXTRACTION/installationMapping.js's own field names 1:1) -> canonical
# installation_report column (snake_case). Full parity with every real
# installation_report column, per MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-
# CORRECTION-001's Phase 10 round-trip requirement ("no meaningful field
# loss") -- the JSONB-shaped fields (site_activities, bill_of_material, the
# four observation lists, post_installation_readings) pass through
# untouched: reviewed_fields/extracted_fields already carry them in the
# exact installation_report-ready shape (date-grouped activities,
# location-aware observation entries), never re-flattened here.
EXTRACTED_TO_INSTALLATION_REPORT_FIELDS: dict[str, str] = {
    "reportNo": "report_no",
    "tsoNo": "tso_no",
    "reportDate": "report_date",
    "customer": "customer",
    "address": "address",
    "plant": "plant",
    "unit": "unit",
    "poNo": "po_no",
    "packingListNo": "packing_list_no",
    "location": "location",
    "equipmentMfr": "equipment_mfr",
    "modelType": "model_type",
    "size": "size",
    "configuration": "configuration",
    "serialNo": "serial_no",
    "plantEquipNo": "plant_equip_no",
    "pumpType": "pump_type",
    "shaftSpeed": "shaft_speed",
    "rotation": "rotation",
    "sealManufacture": "seal_manufacture",
    "sealType": "seal_type",
    "sealArrangement": "seal_arrangement",
    "sealSize": "seal_size",
    "materialCode": "material_code",
    "drawingNo": "drawing_no",
    "sealLocation": "seal_location",
    "liquid": "liquid",
    "temperatureRange": "temperature_range",
    "specificGravity": "specific_gravity",
    "viscosity": "viscosity",
    "flashPoint": "flash_point",
    "boilingPoint": "boiling_point",
    "freezePoint": "freeze_point",
    "vaporPress": "vapor_press",
    "dischargePress": "discharge_press",
    "suctionPress": "suction_press",
    "differentialPress": "differential_press",
    "stuffingBoxPress": "stuffing_box_press",
    "sealPress": "seal_press",
    "corrosionErosionBy": "corrosion_erosion_by",
    "apiPlan": "api_plan",
    "flushLiquid": "flush_liquid",
    "flushPressure": "flush_pressure",
    "flushTemp": "flush_temp",
    "flushFlowrate": "flush_flowrate",
    "bufferBarrierPress": "buffer_barrier_press",
    "bufferBarrierFluid": "buffer_barrier_fluid",
    "quenchFluid": "quench_fluid",
    "sealChamberShaftInspection": "seal_chamber_shaft_inspection",
    "basicSealCondition": "basic_seal_condition",
    "glandCondition": "gland_condition",
    "sleeveCondition": "sleeve_condition",
    "shaftCondition": "shaft_condition",
    "bearingCondition": "bearing_condition",
    "gasketCondition": "gasket_condition",
    "radialBearingNo": "radial_bearing_no",
    "thrustBearingNo": "thrust_bearing_no",
    "summaryIntro": "summary_intro",
    "siteActivityIntro": "site_activity_intro",
    "siteActivities": "site_activities",
    "bomCaption": "bom_caption",
    "billOfMaterial": "bill_of_material",
    "glandObservationNote": "gland_observation_note",
    "glandObservation": "gland_observation",
    "sleeveObservationNote": "sleeve_observation_note",
    "sleeveObservation": "sleeve_observation",
    "retainerDiscObservationNote": "retainer_disc_observation_note",
    "retainerDiscObservation": "retainer_disc_observation",
    "cartridgeDriveCollarObservationNote": "cartridge_drive_collar_observation_note",
    "cartridgeDriveCollarObservation": "cartridge_drive_collar_observation",
    "signatures": "signatures",
    "sourceDocumentName": "source_document_name",
    "postInstallationReadings": "post_installation_readings",
}

# Phase 7 (MWO-LTSA-INSTALLATION-REPORT-STRUCTURAL-CORRECTION-001):
# critical identity fields that must never enter canonical Installation
# merely because a value exists -- their AI-extracted value must also
# carry a confidence score. This is a diagnostic/advisory contract (not a
# hard Save-time block: a human reviewer who has already corrected/
# confirmed a value in reviewed_fields has already done the safety work
# resolve_pump_review_gate/match_pump/match_seal exist to force), used by
# a caller (future review UI/API) to flag which extracted_fields entries
# lack real provenance before asking a human to trust them.
CRITICAL_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {"reportNo", "plantEquipNo", "reportDate", "sealType", "sealSize", "apiPlan"}
)


def missing_field_provenance(extracted_fields: dict[str, Any]) -> list[str]:
    """Returns the CRITICAL_PROVENANCE_FIELDS keys that are either absent
    from extracted_fields or present as a bare value instead of
    AI-EXTRACTION/models.py's own FieldValue(value, confidence) shape --
    i.e. a value exists but its confidence was never recorded. Strengthens
    the existing JSON contract (Phase 7's own preferred direction) rather
    than adding new document_field_extraction columns: field-level
    confidence was already representable by convention; this function
    makes "representable" into an enforceable, testable definition.
    """
    missing = []
    for key in CRITICAL_PROVENANCE_FIELDS:
        entry = extracted_fields.get(key)
        if entry is None:
            missing.append(key)
        elif not (isinstance(entry, dict) and "value" in entry and "confidence" in entry):
            missing.append(key)
    return missing


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
