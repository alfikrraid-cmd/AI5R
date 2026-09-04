"""MWO-LTSA-HISTORICAL-PM-FINALIZATION-001 -- a narrow, explicit
application path that moves a historical-recovery PM occurrence's
workflow_status directly from DRAFT to FINALIZED, bypassing the normal
DRAFT -> SUBMITTED -> FINALIZED digital review workflow
(pm_cm_workflow_service.py, never modified or reused by this module)
ONLY for records that are provably part of the frozen, already-human-
verified historical recovery batch.

This is NOT a general DRAFT -> FINALIZED bypass: eligibility is entirely
server-derived (fetch_finalization_targets(), the same candidate_
identity_v2 recovery-membership rule historical_review.py's own
_is_recovery_candidate() uses), never a client-supplied id list and
never a broad `source_reference LIKE 'document_field_extraction:%'`
predicate. Every invariant from the design (staging status, review
metadata, exact 1:1 source_reference mapping, workflow_status, asset/date
conflict, canonical pump validity) is re-verified read-only here before a
caller may ever attempt the write; any invalid member fails the whole
batch closed -- no partial finalization, same "one script, one atomic
outcome" discipline as historical_pm_promotion_batch_service.py's own
validate_promotion_batch()/promote_pm_batch() pair, which this module
mirrors in shape.

Idempotency: a target whose pm_occurrence is already FINALIZED classifies
as ALREADY_FINALIZED (a safe, no-op outcome, not an error) -- a retry of
the same request after a prior full success touches nothing and writes
no additional audit row.
"""

from __future__ import annotations

from typing import Any, Protocol

_ELIGIBLE_DOMAIN = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
_ELIGIBLE_STAGING_STATUS = "SAVED"


class FinalizationBatchError(ValueError):
    pass


class StagingRepositoryProtocol(Protocol):
    def list_by_status(self, status: str, detected_document_type: str | None = None) -> list[dict[str, Any]]: ...


class PMOccurrenceRepositoryProtocol(Protocol):
    def find_by_source_references(self, source_references: list[str]) -> list[dict[str, Any]]: ...
    def find_by_asset_dates(self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]: ...
    def find_valid_pump_tags(self, tags: list[str]) -> set[str]: ...
    def finalize_historical_batch_atomic(
        self, pm_occurrence_codes: list[str], *, finalized_by: str
    ) -> list[dict[str, Any]]: ...


def _is_recovery_candidate(candidate: dict[str, Any]) -> bool:
    if candidate.get("detected_document_type") != _ELIGIBLE_DOMAIN:
        return False
    fields = candidate.get("extracted_fields") or {}
    return bool(fields.get("candidate_identity_v2"))


def fetch_finalization_targets(staging_repository: StagingRepositoryProtocol) -> list[dict[str, Any]]:
    """Server-derived recovery-batch membership for FINALIZATION: the
    SAME candidate_identity_v2 recovery rule historical_review.py's own
    _is_recovery_candidate() uses, restricted to SAVED (a candidate whose
    promotion has already completed -- PENDING_REVIEW/REVIEWED members
    were never promoted and have no pm_occurrence row to finalize).
    Never a client-supplied id list, never a broad source_reference LIKE
    predicate -- membership is decided ONLY by staging-table columns."""
    saved = staging_repository.list_by_status(_ELIGIBLE_STAGING_STATUS, _ELIGIBLE_DOMAIN)
    return [c for c in saved if _is_recovery_candidate(c)]


def _classify_one(
    candidate: dict[str, Any],
    pm_by_source_reference: dict[str, list[dict[str, Any]]],
    conflict_by_asset_date: dict[tuple[str, str], list[dict[str, Any]]],
    valid_pump_tags: set[str],
) -> dict[str, Any]:
    """Pure, read-only classification -- zero DB calls. Every branch maps
    directly to one of the design's 13 fail-closed eligibility items."""
    candidate_id = candidate["document_field_extraction_id"]

    # Items 3/4/5 (domain + candidate_identity_v2 + SAVED) -- domain/
    # identity are already guaranteed by fetch_finalization_targets()'s
    # own filter; only staging status is re-checked here defensively.
    if candidate.get("status") != _ELIGIBLE_STAGING_STATUS:
        return {"candidate_id": candidate_id, "status": "WRONG_STAGING_STATUS"}
    # Items 6/7
    if not candidate.get("reviewed_by"):
        return {"candidate_id": candidate_id, "status": "MISSING_REVIEWED_BY"}
    if not candidate.get("reviewed_at"):
        return {"candidate_id": candidate_id, "status": "MISSING_REVIEWED_AT"}

    # Item 1: source_reference exactly resolves to
    # document_field_extraction:<candidate_id>.
    source_reference = f"document_field_extraction:{candidate_id}"
    matches = pm_by_source_reference.get(source_reference, [])
    # Items 8/11: exists exactly once / no duplicate.
    if len(matches) == 0:
        return {"candidate_id": candidate_id, "status": "MISSING_PM_OCCURRENCE", "source_reference": source_reference}
    if len(matches) > 1:
        return {"candidate_id": candidate_id, "status": "DUPLICATE_SOURCE_REFERENCE", "source_reference": source_reference}

    pm = matches[0]
    asset_code = pm.get("asset_code")
    occurrence_date = pm.get("occurrence_date")

    # Item 13: canonical pump is valid (exists exactly once in ltsa_pumps).
    if asset_code not in valid_pump_tags:
        return {
            "candidate_id": candidate_id, "status": "INVALID_PUMP",
            "pm_occurrence_code": pm["pm_occurrence_code"], "source_reference": source_reference,
        }

    # Item 12: no asset/date conflict against a DIFFERENT pm_occurrence
    # row. find_by_asset_dates() always returns this candidate's OWN row
    # too (it already exists at this (asset, date)) alongside any
    # genuine conflict -- so every row at this key must be checked, not
    # just the first one returned, or a same-key conflict could hide
    # behind the candidate's own row happening to be listed first.
    same_key_rows = conflict_by_asset_date.get((asset_code, occurrence_date), [])
    if any(r.get("source_reference") != source_reference for r in same_key_rows):
        return {
            "candidate_id": candidate_id, "status": "ASSET_DATE_CONFLICT",
            "pm_occurrence_code": pm["pm_occurrence_code"], "source_reference": source_reference,
        }

    # Item 9: workflow_status = DRAFT. Already-FINALIZED is a distinct,
    # SAFE no-op outcome (idempotent retry), never lumped with a genuine
    # stuck-state error.
    if pm.get("workflow_status") == "FINALIZED":
        return {
            "candidate_id": candidate_id, "status": "ALREADY_FINALIZED",
            "pm_occurrence_code": pm["pm_occurrence_code"], "source_reference": source_reference,
        }
    if pm.get("workflow_status") != "DRAFT":
        return {
            "candidate_id": candidate_id, "status": "NOT_DRAFT",
            "pm_occurrence_code": pm["pm_occurrence_code"], "source_reference": source_reference,
            "workflow_status": pm.get("workflow_status"),
        }

    # Item 10 (belongs to the exact recovery population) is inherent:
    # this pm_occurrence row was only ever reached via THIS candidate's
    # own source_reference -- no other lookup path exists here.
    return {
        "candidate_id": candidate_id, "status": "ELIGIBLE",
        "pm_occurrence_code": pm["pm_occurrence_code"], "source_reference": source_reference,
    }


def validate_finalization_batch(
    staging_repository: StagingRepositoryProtocol,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol,
) -> dict[str, Any]:
    """Read-only. Never finalizes. Set-based/batched: a small, bounded
    number of queries (list_by_status, find_by_source_references,
    find_by_asset_dates, find_valid_pump_tags -- four total) regardless
    of how many candidates the recovery batch contains, never one query
    per candidate."""
    targets = fetch_finalization_targets(staging_repository)
    if not targets:
        return {"results": [], "counts": {}, "all_eligible": True, "eligible_pm_occurrence_codes": []}

    source_references = [f"document_field_extraction:{c['document_field_extraction_id']}" for c in targets]
    pm_by_source_reference: dict[str, list[dict[str, Any]]] = {}
    for row in pm_occurrence_repository.find_by_source_references(source_references):
        pm_by_source_reference.setdefault(row["source_reference"], []).append(row)

    # Only well-formed (exactly-one-match) rows are worth conflict/pump
    # checking -- a MISSING/DUPLICATE candidate is already classified by
    # _classify_one without needing these lookups to resolve for it.
    well_formed_rows = [rows[0] for rows in pm_by_source_reference.values() if len(rows) == 1]
    pairs = sorted({(row["asset_code"], row["occurrence_date"]) for row in well_formed_rows})
    conflict_by_asset_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in pm_occurrence_repository.find_by_asset_dates(pairs):
        key = (row["asset_code"], row["occurrence_date"])
        conflict_by_asset_date.setdefault(key, []).append(row)

    pump_tags = sorted({row["asset_code"] for row in well_formed_rows if row.get("asset_code")})
    valid_pump_tags = pm_occurrence_repository.find_valid_pump_tags(pump_tags)

    results = [
        _classify_one(c, pm_by_source_reference, conflict_by_asset_date, valid_pump_tags)
        for c in targets
    ]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    # ALREADY_FINALIZED is a valid, safe-no-op outcome (exact retry after
    # a prior full success) -- only a genuinely ineligible/conflicting
    # entry blocks the batch.
    eligible_statuses = {"ELIGIBLE", "ALREADY_FINALIZED"}
    all_eligible = all(r["status"] in eligible_statuses for r in results)
    eligible_pm_occurrence_codes = [r["pm_occurrence_code"] for r in results if r["status"] == "ELIGIBLE"]
    return {
        "results": results, "counts": counts, "all_eligible": all_eligible,
        "eligible_pm_occurrence_codes": eligible_pm_occurrence_codes,
    }


def finalization_readiness(
    staging_repository: StagingRepositoryProtocol,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol,
) -> dict[str, Any]:
    """Read-only status summary backing GET .../recovery/pm/finalization-
    status. finalization_ready means "there is at least one genuinely
    DRAFT, eligible target right now" -- it is False both before any
    target exists and after every target is already FINALIZED, an
    honest reflection of whether the Finalize action currently does
    anything, never a one-time "was this batch ever ready" flag."""
    precheck = validate_finalization_batch(staging_repository, pm_occurrence_repository)
    counts = precheck["counts"]
    draft_count = counts.get("ELIGIBLE", 0)
    finalized_count = counts.get("ALREADY_FINALIZED", 0)
    target_count = sum(counts.values())
    invalid_count = target_count - draft_count - finalized_count
    return {
        "target_count": target_count,
        "draft_count": draft_count,
        "finalized_count": finalized_count,
        "invalid_count": invalid_count,
        "finalization_ready": draft_count > 0,
    }


def finalize_historical_pm_batch(
    staging_repository: StagingRepositoryProtocol,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol,
    *,
    finalized_by: str,
) -> dict[str, Any]:
    """Fail-closed: validates the ENTIRE server-derived population first
    (read-only); if any target is genuinely ineligible (not ELIGIBLE/
    ALREADY_FINALIZED), finalizes NOTHING. If every target passes, calls
    PMOccurrenceRepository.finalize_historical_batch_atomic() ONCE with
    only the genuinely-DRAFT codes -- already-FINALIZED targets are
    excluded from the write entirely (idempotent no-op), and if every
    eligible target is already FINALIZED (or there are zero targets at
    all) this returns a zero-mutation success without ever calling the
    atomic method."""
    precheck = validate_finalization_batch(staging_repository, pm_occurrence_repository)
    if not precheck["all_eligible"]:
        return {"results": [], "precheck": precheck, "status": "REJECTED_PRECHECK_FAILED", "finalized_count": 0}

    codes_to_finalize = precheck["eligible_pm_occurrence_codes"]
    if not codes_to_finalize:
        return {"results": [], "precheck": precheck, "status": "FINALIZED", "finalized_count": 0}

    try:
        rows = pm_occurrence_repository.finalize_historical_batch_atomic(
            codes_to_finalize, finalized_by=finalized_by,
        )
    except Exception as error:  # noqa: BLE001 -- DB driver exception type varies; means the atomic script's own DO block raised and Postgres rolled everything back
        return {"results": [], "precheck": precheck, "status": "REJECTED_ATOMIC_TRANSACTION_FAILED", "error": str(error), "finalized_count": 0}
    if len(rows) != len(codes_to_finalize):
        raise FinalizationBatchError(
            f"atomic batch finalize returned {len(rows)} rows for {len(codes_to_finalize)} requested codes"
        )
    return {"results": rows, "precheck": precheck, "status": "FINALIZED", "finalized_count": len(rows)}


__all__ = [
    "FinalizationBatchError",
    "StagingRepositoryProtocol",
    "PMOccurrenceRepositoryProtocol",
    "fetch_finalization_targets",
    "validate_finalization_batch",
    "finalization_readiness",
    "finalize_historical_pm_batch",
]
