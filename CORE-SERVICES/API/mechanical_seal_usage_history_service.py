"""MWO-LTSA-SEAL-USAGE-HISTORY-READ-MODEL-001 (R2I) -- pure read-time
projection over installation_report + seal_registry into a
UsageHistoryEvent shape, per the R2H design (Option 1: no new table, no
migration, no persistence).

CRITICAL, EXPLICIT SCOPE LIMIT (R2C's own finding, carried forward):
installation_report has NO structured intervention_type/subtype column
anywhere -- only free-text/JSONB narrative fields (summary_intro,
site_activities, bill_of_material). R2C proved this vendor's own
boilerplate SUMMARY sentence is not reliable evidence, and that BOM
"Replace" lines never imply complete-seal replacement without further,
careful, non-heuristic reading. This module therefore NEVER attempts to
derive primary_intervention/intervention_actions from those fields --
every event reports INTERVENTION_TYPE="UNKNOWN" with
intervention_review_status="NOT_DERIVABLE_FROM_STRUCTURED_DATA". This is
the mission's own explicitly-sanctioned "evidence-safe portion" of the
read model, not an oversight. A future MWO may add a real structured
intervention-classification column/process; until then, this module
must not guess.

Master association IS derivable live, safely: seal_type/seal_size are
real (if free-text) columns on installation_report, and the exact-match
rule below is a direct, unmodified port of
seal_installation_report_linkage_classification.sql's own canonical
Part B logic (NORMALIZED_EXACT_SEAL_TYPE + VERIFIED_EXACT_SHAFT_SIZE) --
never a new algorithm, never fuzzy/substring matching.

Provenance is derived from a real structural signal only: whether the
report's own plant_equip_no (raw, always-present) and pump_tag_number
(only ever set by a separate, explicit, reviewed linking process --
installation_fitment_service.py) disagree when both are present. This
is narrower than R2C's manual multi-field PDF cross-reference (which
also caught contradictions inside free-text SUMMARY sentences no
structured column captures) -- disclosed, not overclaimed.
"""

from __future__ import annotations

import re
from typing import Any

_FRACTION_SIZE_RE = re.compile(r'^\s*(\d+)\.(\d+)/(\d+)\s*"?\s*$')
_DECIMAL_INCH_SIZE_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*"\s*$')
_MM_SIZE_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*MM\s*$', re.IGNORECASE)


def parse_seal_size(raw: str | None) -> float | None:
    """Exact port of the canonical classifier's `parsed_size` CASE
    expression (seal_installation_report_linkage_classification.sql,
    Part B) -- same three patterns, same order, same semantics. Returns
    None (never a guess) for anything else, including compound/dual
    values."""
    if raw is None:
        return None
    text = raw.strip()
    if text in ("", "-"):
        return None

    match = _FRACTION_SIZE_RE.match(text)
    if match:
        whole, numerator, denominator = (int(match.group(i)) for i in (1, 2, 3))
        if denominator == 0:
            return None
        return whole + numerator / denominator

    match = _DECIMAL_INCH_SIZE_RE.match(text)
    if match:
        return float(match.group(1))

    match = _MM_SIZE_RE.match(text)
    if match:
        return float(match.group(1))

    return None


def normalize_seal_type(raw: str | None) -> str | None:
    """Trimmed, case-insensitive normalization -- matches the classifier's
    own `btrim(upper(...))` comparison exactly. Never infers a missing
    value."""
    if raw is None:
        return None
    text = raw.strip()
    return text.upper() if text else None


def classify_master_association(
    seal_type: str | None,
    seal_size: str | None,
    registry_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Direct, unmodified port of the canonical classifier's type_candidates
    / size_candidates / classification CASE logic. registry_rows are
    real seal_registry rows (seal_code, seal_name, shaft_size) as
    returned by the existing SealGateway -- never a diagnostic CSV.

    Returns {classifier_class, master_seal_code, candidate_count}.
    classifier_class in {"A","B","C","D"}; master_seal_code is set only
    for "A". No fuzzy/substring matching anywhere below.
    """
    normalized_type = normalize_seal_type(seal_type)
    parsed_size = parse_seal_size(seal_size)

    if normalized_type is None:
        return {"classifier_class": "D", "master_seal_code": None, "candidate_count": 0}

    type_candidates = [
        row for row in registry_rows
        if normalize_seal_type(row.get("seal_name")) == normalized_type
    ]
    if not type_candidates:
        return {"classifier_class": "C", "master_seal_code": None, "candidate_count": 0}

    if parsed_size is None:
        return {"classifier_class": "D", "master_seal_code": None, "candidate_count": 0}

    size_candidates = []
    for row in type_candidates:
        shaft_size = row.get("shaft_size")
        if shaft_size is None:
            continue
        try:
            shaft_size = float(shaft_size)
        except (TypeError, ValueError):
            continue
        if abs(shaft_size - parsed_size) < 0.01:
            size_candidates.append(row)

    distinct_codes = sorted({row["seal_code"] for row in size_candidates})
    if not distinct_codes:
        return {"classifier_class": "C", "master_seal_code": None, "candidate_count": 0}
    if len(distinct_codes) == 1:
        return {"classifier_class": "A", "master_seal_code": distinct_codes[0], "candidate_count": 1}
    return {"classifier_class": "B", "master_seal_code": None, "candidate_count": len(distinct_codes)}


_MASTER_ASSOCIATION_STATUS_BY_CLASS = {"A": "CONFIRMED", "B": "AMBIGUOUS", "C": "UNRESOLVED", "D": "UNRESOLVED"}


def derive_provenance_status(plant_equip_no: str | None, pump_tag_number: str | None) -> str:
    """HOLD only on a real, structural signal: both fields are present
    and disagree once trimmed/uppercased. Never inspects free text
    (summary/site_activities) -- that category of contradiction (R2C's
    INSTL-025/041 cases) is not detectable from structured columns alone
    and is NOT claimed to be caught here."""
    a = (plant_equip_no or "").strip().upper()
    b = (pump_tag_number or "").strip().upper()
    if a and b and a != b:
        return "HOLD"
    return "CLEAR"


def project_usage_history_event(
    installation_row: dict[str, Any],
    registry_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Builds one UsageHistoryEvent (R2H's conceptual shape) from one real
    installation_report row + the full real seal_registry row set. Pure
    function -- no DB/gateway call inside."""
    classification = classify_master_association(
        installation_row.get("seal_type"), installation_row.get("seal_size"), registry_rows
    )
    classifier_class = classification["classifier_class"]

    plant_equip_no = installation_row.get("plant_equip_no")
    pump_tag_number = installation_row.get("pump_tag_number")
    provenance_status = derive_provenance_status(plant_equip_no, pump_tag_number)

    master_association_status = _MASTER_ASSOCIATION_STATUS_BY_CLASS[classifier_class]
    if provenance_status == "HOLD":
        # Mandatory override (R2G precedent, INSTL-041-2026): a contradictory
        # source identity is never presented as a safe association, regardless
        # of how clean the type/size match looks. The diagnostic candidate
        # (classification["master_seal_code"], below) is still carried, not
        # hidden -- only "approvable" (master_association_approvable) is
        # forced false.
        master_association_status = "PROVENANCE_HOLD"

    return {
        "event_id": installation_row.get("installation_code"),
        "event_date": installation_row.get("report_date"),
        "pump_tag": pump_tag_number or plant_equip_no,
        "master_seal_code": classification["master_seal_code"] if classifier_class == "A" else None,
        "master_seal_id": "N/A",
        "master_association_status": master_association_status,
        "master_association_approvable": master_association_status == "CONFIRMED",
        "classifier_class": classifier_class,
        "intervention_type": "UNKNOWN",
        "intervention_actions": [],
        "detail": "Intervention type not derivable from structured data; manual/engineering review required.",
        "source_type": "INSTALLATION_REPORT",
        "source_id": installation_row.get("installation_code"),
        "provenance_status": provenance_status,
        "physical_seal_unit_id": None,
        "physical_unit_identity_status": "NOT_PROVABLE",
        "warranty_status": "N/A",
        "running_days": None,
        "review": {
            "intervention": "NOT_DERIVABLE_FROM_STRUCTURED_DATA",
            "master_association": "NEEDS_REVIEW" if master_association_status != "CONFIRMED" else "RESOLVED",
            "provenance": "CONTRADICTION_FOUND" if provenance_status == "HOLD" else "CLEAR",
        },
    }


def list_seal_usage_history(
    installations: list[dict[str, Any]],
    registry_rows: list[dict[str, Any]],
    seal_code: str,
) -> list[dict[str, Any]]:
    """Seal-centric view: ONLY events whose OWN type+size deterministically
    resolves to this exact seal_code, with a clean (non-HOLD) provenance
    status. Never includes an event merely because its pump happens to be
    compatible with this seal -- compatibility is a different table
    (seal_pump_compatibility) never consulted here."""
    events = [project_usage_history_event(row, registry_rows) for row in installations]
    matching = [
        event for event in events
        if event["master_association_status"] == "CONFIRMED" and event["master_seal_code"] == seal_code
    ]
    return sorted(matching, key=lambda event: (event["event_date"] or "", event["event_id"] or ""), reverse=True)


def list_pump_seal_usage_history(
    installations: list[dict[str, Any]],
    registry_rows: list[dict[str, Any]],
    pump_tag: str,
) -> list[dict[str, Any]]:
    """Pump-centric view: every intervention recorded for this exact pump
    tag, regardless of master-association resolution -- unresolved/
    ambiguous/provenance-hold rows are never discarded (R2H section 6).

    pump_tag_number (only ever set by the separate, explicit, reviewed
    fitment-linking process) takes precedence over the raw, always-present
    plant_equip_no when both exist -- once a report has been reviewed and
    confirmed against a specific pump, that confirmed identity is
    authoritative and the stale raw value must no longer also match a
    query for some other, older tag."""
    normalized_tag = pump_tag.strip().upper()

    def _matches(row: dict[str, Any]) -> bool:
        effective_tag = row.get("pump_tag_number") or row.get("plant_equip_no")
        return (effective_tag or "").strip().upper() == normalized_tag

    matching_rows = [row for row in installations if _matches(row)]
    events = [project_usage_history_event(row, registry_rows) for row in matching_rows]
    return sorted(events, key=lambda event: (event["event_date"] or "", event["event_id"] or ""), reverse=True)
