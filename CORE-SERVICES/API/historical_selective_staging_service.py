"""MWO-LTSA-SELECTIVE-HISTORICAL-STAGING-001 -- stages an EXACT,
prevalidated candidate manifest through document_field_extraction,
without weakening or replacing the existing general file-staging
workflow (historical_pm_cmon_cli.py stage / stage_area_candidates()) --
that path stages every PM+CMON+Finding candidate found in one source
file, unconditionally; it remains useful for normal/manual ingestion.
This module is additive: a second, narrower entry point for a bounded,
already-classified recovery batch (e.g. Phase 2's 540 verified
NEW_HIGH_CONFIDENCE PM candidates) that must never pull in sibling
CMON/Finding candidates or excluded/ambiguous/duplicate PM rows just
because they share a source file.

Stable candidate identity: (normalized_workbook, source_sheet_name,
source_row_number), hashed via the EXISTING build_pm_occurrence_code_v2/
build_condition_monitoring_reading_code_v2 (ltsa_hoc_pm_cm_upsert.py) --
not invented here. The legacy V1 code (source_sheet_name+source_row_number
only, no workbook identity) is confirmed, in this repo's own MWO-LTSA-PM-
CMON-DETERMINISTIC-ID-FIX-015B1 comment, to collide across different
months' files that share template sheet names/row numbers -- unsafe as a
dedup key. (canonical_tag, occurrence_date) is even less safe: the one
real source duplicate found in this archive (110-P-11A, 2026-01-06)
proves two SOURCE ROWS can share a (tag, date) pair while a genuine
same-day double-visit could too -- neither case is distinguishable by
(tag, date) alone. Identity lives in extracted_fields (JSONB, already
exists) as candidate_identity_v2 -- no schema migration.

Never rediscovers candidates: every field this service checks must
already be present on the input manifest entry, supplied by the caller
from an already-completed, already-reviewed extraction/reconciliation
pass (Phase 2). This service only re-verifies what could have drifted
since that pass (live pump roster, live staging-identity collisions) --
it never re-parses a source file or re-derives a classification.
"""

from __future__ import annotations

from typing import Any, Protocol


class SelectiveStagingError(ValueError):
    pass


class WrongDomainError(SelectiveStagingError):
    pass


class NotEligibleError(SelectiveStagingError):
    pass


class UnknownPumpTagError(SelectiveStagingError):
    pass


class AmbiguousPumpTagError(SelectiveStagingError):
    pass


class InvalidCandidateError(SelectiveStagingError):
    pass


class StagingRepositoryProtocol(Protocol):
    def find_by_stable_identity(self, candidate_identity_v2: str) -> dict[str, Any] | None: ...
    def count_canonical_pump_matches(self, pump_tag_number: str) -> int: ...
    def stage_verified_batch(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
    def final_pm_occurrence_exists(self, *, asset_code: str, occurrence_date: str) -> bool: ...


_DETECTED_TYPE_BY_DOMAIN = {
    "PM": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
    "CMON": "HISTORICAL_CMON_READING_CANDIDATE",
    "FINDING": "HISTORICAL_FINDING_CANDIDATE",
}
_ELIGIBLE_RECOVERY_CLASSES = frozenset({"NEW_HIGH_CONFIDENCE"})


def _validate_one(repository: StagingRepositoryProtocol, manifest_entry: dict[str, Any], *, expected_domain: str) -> dict[str, Any]:
    """Read-only. Never stages. Returns a status dict; never raises --
    batch validation needs every entry's outcome, not just the first."""
    identity = manifest_entry.get("candidate_identity_v2")
    canonical_tag = manifest_entry.get("canonical_tag")
    domain = manifest_entry.get("domain")
    recovery_class = manifest_entry.get("recovery_class")

    if not identity or not canonical_tag or not manifest_entry.get("occurrence_date"):
        return {**manifest_entry, "status": "INVALID", "reason": "missing candidate_identity_v2/canonical_tag/occurrence_date"}
    if domain != expected_domain:
        return {**manifest_entry, "status": "WRONG_DOMAIN", "reason": f"expected {expected_domain}, got {domain!r}"}
    if recovery_class not in _ELIGIBLE_RECOVERY_CLASSES:
        return {**manifest_entry, "status": "NOT_ELIGIBLE", "reason": f"recovery_class {recovery_class!r} not eligible"}

    match_count = repository.count_canonical_pump_matches(canonical_tag)
    if match_count == 0:
        return {**manifest_entry, "status": "UNKNOWN_PUMP"}
    if match_count > 1:
        return {**manifest_entry, "status": "AMBIGUOUS_PUMP"}

    existing = repository.find_by_stable_identity(identity)
    if existing is not None:
        return {**manifest_entry, "status": "ALREADY_STAGED", "existing_id": existing["document_field_extraction_id"]}

    if expected_domain == "PM" and repository.final_pm_occurrence_exists(
        asset_code=canonical_tag, occurrence_date=manifest_entry["occurrence_date"]
    ):
        return {**manifest_entry, "status": "FINAL_PM_ALREADY_EXISTS"}

    return {**manifest_entry, "status": "VALID"}


def validate_selective_staging_batch(
    repository: StagingRepositoryProtocol, manifest: list[dict[str, Any]], *, expected_domain: str = "PM"
) -> dict[str, Any]:
    """Read-only. Never stages, regardless of outcome."""
    results = [_validate_one(repository, m, expected_domain=expected_domain) for m in manifest]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"results": results, "counts": counts, "all_valid": counts.get("VALID", 0) == len(results)}


def _to_repository_row(manifest_entry: dict[str, Any], *, expected_domain: str) -> dict[str, Any]:
    fields = dict(manifest_entry["fields"])
    fields["candidate_identity_v2"] = manifest_entry["candidate_identity_v2"]
    fields["source_workbook"] = manifest_entry.get("source_workbook")
    fields["source_sheet_name"] = manifest_entry.get("source_sheet_name")
    fields["source_row_number"] = manifest_entry.get("source_row_number")
    fields["raw_asset_tag"] = manifest_entry.get("raw_asset_tag", manifest_entry["canonical_tag"])
    return {
        "candidate_identity_v2": manifest_entry["candidate_identity_v2"],
        "source_document_id": manifest_entry.get("source_document_id") or f"SELECTIVE-{manifest_entry.get('source_batch', 'unknown')}",
        "detected_document_type": _DETECTED_TYPE_BY_DOMAIN[expected_domain],
        "extracted_fields": fields,
        "pump_tag_number": manifest_entry["canonical_tag"],
        "source_page": manifest_entry.get("source_page"),
    }


def stage_verified_candidates(
    repository: StagingRepositoryProtocol, manifest: list[dict[str, Any]], *, expected_domain: str = "PM"
) -> dict[str, Any]:
    """Fail-closed, true single-transaction stage. Validates every entry
    first (read-only); if any is not VALID, stages NOTHING. If all are
    VALID, calls repository.stage_verified_batch() ONCE with all N rows
    -- Postgres's own implicit-transaction guarantee (same mechanism as
    the installation-attribution atomic batch fix) makes the actual
    write all-or-nothing."""
    precheck = validate_selective_staging_batch(repository, manifest, expected_domain=expected_domain)
    if not precheck["all_valid"]:
        return {"staged": [], "precheck": precheck, "status": "REJECTED_PRECHECK_FAILED"}

    rows = [_to_repository_row(m, expected_domain=expected_domain) for m in manifest]
    try:
        staged = repository.stage_verified_batch(rows)
    except Exception as error:  # noqa: BLE001 -- DB driver exception type varies; means the script's own DO block raised and Postgres rolled everything back
        return {"staged": [], "precheck": precheck, "status": "REJECTED_ATOMIC_TRANSACTION_FAILED", "error": str(error)}
    if len(staged) != len(manifest):
        raise SelectiveStagingError(f"atomic stage returned {len(staged)} rows for {len(manifest)} manifest entries")
    return {"staged": staged, "precheck": precheck, "status": "STAGED"}


__all__ = [
    "SelectiveStagingError",
    "WrongDomainError",
    "NotEligibleError",
    "UnknownPumpTagError",
    "AmbiguousPumpTagError",
    "InvalidCandidateError",
    "StagingRepositoryProtocol",
    "validate_selective_staging_batch",
    "stage_verified_candidates",
]
