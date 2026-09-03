"""MWO-LTSA-HISTORICAL-PM-RECOVERY-001 -- read-only pre-flight validation
for the deterministic historical PM recovery manifest, BEFORE any
candidate is staged (historical_pm_cmon_cli.py stage) or promoted
(historical_pm_cmon_promotion_service.promote_pm_occurrence_atomic).

This module writes nothing, ever -- it only classifies each candidate
against LIVE pm_occurrence + ltsa_pumps state so a caller can decide
what's actually safe to run through the existing stage -> review ->
promote pipeline. It is not a second ingestion engine: staging and
promotion remain exclusively historical_pm_cmon_cli.py/
historical_pm_cmon_promotion_service.py's job, reused unmodified.

Dedup key: (canonical pump_tag_number, occurrence_date). Verified, not
assumed: pm_occurrence has NO database-level uniqueness constraint on
(asset_code, occurrence_date) -- migration 023 defines only a plain
index, and the schema architecturally permits multiple real PM events
for the same pump on the same date. This key is therefore a validated
heuristic for THIS batch, not a schema-enforced guarantee: the one
real (tag, date) collision found in the July-2026-preceding historical
archive (110-P-11A, 2026-01-06, HOC) was individually inspected against
the raw source XLSX and confirmed to be a true duplicate row (identical
API plan/status/every populated column, differing only by spreadsheet
row number) -- not two distinct legitimate occurrences. A future batch
with a genuine same-day double-visit would need the same manual check,
not blind trust in this key.

promote_pm_occurrence_atomic()'s own real idempotency guarantee is
source_reference-based (pm_occurrence.source_reference ->
AlreadyPromotedError), not date-based -- this module's ALREADY_EXISTS
check exists to catch the DIFFERENT case: a pre-existing pm_occurrence
row that has no source_reference at all (entered through some other
path) and would otherwise be silently duplicated by a new historical
promotion.
"""

from __future__ import annotations

from typing import Any, Protocol


class LivePmStateProtocol(Protocol):
    def count_canonical_pump_matches(self, pump_tag_number: str) -> int: ...
    def occurrence_exists(self, *, asset_code: str, occurrence_date: str) -> bool: ...


def validate_pm_recovery_candidate(
    state: LivePmStateProtocol,
    *,
    canonical_tag: str,
    occurrence_date: str | None,
    seen_keys: set[tuple[str, str]],
    source_classification: str | None = None,
) -> dict[str, Any]:
    """Read-only. `seen_keys` is the caller's own running set across one
    validation batch -- mutated in place on a VALID/ALREADY_EXISTS
    outcome so a second candidate sharing the same key within the SAME
    batch is caught as SOURCE_DUPLICATE, mirroring Phase 2's own
    within-run dedup. `source_classification`, when supplied, must be
    exactly "PM" -- this module recovers PM occurrences only; a
    CM Measuring Report / Finding / installation-report candidate fed in
    by caller error is rejected here rather than silently promoted as if
    it were PM (the Semantic Freeze this whole recovery arc has enforced
    throughout: CM Measuring Report data is Condition Monitoring, never
    Corrective Maintenance or PM)."""
    if source_classification is not None and source_classification != "PM":
        return {
            "canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "INVALID",
            "reason": f"source_classification {source_classification!r} is not PM",
        }
    if not occurrence_date:
        return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "INVALID", "reason": "missing occurrence_date"}

    match_count = state.count_canonical_pump_matches(canonical_tag)
    if match_count == 0:
        return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "UNKNOWN_PUMP"}
    if match_count > 1:
        return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "AMBIGUOUS_PUMP"}

    key = (canonical_tag, occurrence_date)
    if key in seen_keys:
        return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "SOURCE_DUPLICATE"}

    if state.occurrence_exists(asset_code=canonical_tag, occurrence_date=occurrence_date):
        seen_keys.add(key)
        return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "ALREADY_EXISTS"}

    seen_keys.add(key)
    return {"canonical_tag": canonical_tag, "occurrence_date": occurrence_date, "status": "VALID_NEW"}


def validate_pm_recovery_batch(state: LivePmStateProtocol, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """`candidates`: [{"canonical_tag": ..., "occurrence_date": ..., ...any
    other manifest fields the caller wants echoed back}, ...]. Read-only;
    never stages or promotes anything."""
    seen_keys: set[tuple[str, str]] = set()
    results = []
    for c in candidates:
        outcome = validate_pm_recovery_candidate(
            state,
            canonical_tag=c["canonical_tag"],
            occurrence_date=c.get("occurrence_date"),
            seen_keys=seen_keys,
            source_classification=c.get("source_classification"),
        )
        results.append({**c, **outcome})
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"results": results, "counts": counts}


__all__ = ["LivePmStateProtocol", "validate_pm_recovery_candidate", "validate_pm_recovery_batch"]
