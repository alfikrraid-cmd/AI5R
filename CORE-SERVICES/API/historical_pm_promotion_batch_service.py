"""MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- exact-batch sibling of historical_
pm_cmon_promotion_service.promote_pm_occurrence_atomic(). Same two-phase
shape as historical_selective_staging_service.py / historical_bulk_
review_service.py: a read-only validate pass over an explicit,
caller-supplied candidate_id list, then ONE atomic write
(PMOccurrenceRepository.promote_historical_pm_batch_atomic()) that only
runs if every id validated. Never rediscovers membership via a broad
predicate (all REVIEWED / all PM / ...) -- the caller always supplies
the exact frozen id list.

Idempotency: a candidate already in status SAVED, with a pm_occurrence
row matching its own source_reference, validates as ALREADY_PROMOTED
(not an error) -- a retry of the same batch after a prior full success
is a safe no-op, matching the exact-retry requirement. A candidate
mapped to a DIFFERENT candidate's already-final (asset_code,
occurrence_date) validates as CONFLICT and fails the whole batch
(fail-closed) -- promotion never guesses past a real conflict.
"""

from __future__ import annotations

from typing import Any, Protocol

MAX_PROMOTION_BATCH = 1000
_ELIGIBLE_DOMAIN = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
_ELIGIBLE_STATUSES = frozenset({"REVIEWED", "SAVED"})


class PromotionBatchError(ValueError):
    pass


class BatchTooLargeError(PromotionBatchError):
    pass


class EmptyBatchError(PromotionBatchError):
    pass


class DuplicateCandidateIdError(PromotionBatchError):
    pass


class StagingRepositoryProtocol(Protocol):
    def find_by_id(self, candidate_id: str) -> dict[str, Any] | None: ...
    def find_by_ids(self, candidate_ids: list[str]) -> list[dict[str, Any]]: ...


class PMOccurrenceRepositoryProtocol(Protocol):
    def find_by_source_reference(self, source_reference: str) -> dict[str, Any] | None: ...
    def find_by_source_references(self, source_references: list[str]) -> list[dict[str, Any]]: ...
    def find_by_asset_and_date(self, asset_code: str, occurrence_date: str) -> dict[str, Any] | None: ...
    def find_by_asset_dates(self, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]: ...
    def promote_historical_pm_batch_atomic(
        self, candidate_ids: list[str], *, pm_schedule_code: str, promoted_by: str
    ) -> list[dict[str, Any]]: ...


def _classify_one(
    candidate_id: str,
    candidates_by_id: dict[str, dict[str, Any]],
    already_by_source_reference: dict[str, dict[str, Any]],
    conflict_by_asset_date: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Pure, read-only classification -- zero DB calls. Identical rule
    set/ordering to the original per-candidate _validate_one() (removed
    MWO-LTSA-RECOVERY-STATUS-LATENCY-001), just reading from lookup
    dicts validate_promotion_batch() batch-fetched once up front instead
    of one live query per candidate."""
    candidate = candidates_by_id.get(candidate_id)
    if candidate is None:
        return {"candidate_id": candidate_id, "status": "NOT_FOUND"}
    if candidate.get("detected_document_type") != _ELIGIBLE_DOMAIN:
        return {"candidate_id": candidate_id, "status": "WRONG_DOMAIN"}
    if candidate.get("status") not in _ELIGIBLE_STATUSES:
        return {"candidate_id": candidate_id, "status": "WRONG_STATUS"}
    pump_tag = candidate.get("pump_tag_number")
    if not pump_tag:
        return {"candidate_id": candidate_id, "status": "UNKNOWN_PUMP"}
    fields = candidate.get("reviewed_fields") or candidate.get("extracted_fields") or {}
    occurrence_date = fields.get("occurrence_date")
    if not occurrence_date:
        return {"candidate_id": candidate_id, "status": "INVALID_FIELDS", "reason": "missing occurrence_date"}

    source_reference = f"document_field_extraction:{candidate_id}"
    already = already_by_source_reference.get(source_reference)
    if already is not None:
        return {"candidate_id": candidate_id, "status": "ALREADY_PROMOTED", "pm_occurrence_code": already["pm_occurrence_code"]}

    existing_for_date = conflict_by_asset_date.get((pump_tag, occurrence_date))
    if existing_for_date is not None and existing_for_date.get("source_reference") != source_reference:
        return {"candidate_id": candidate_id, "status": "CONFLICT", "pm_occurrence_code": existing_for_date["pm_occurrence_code"]}

    return {"candidate_id": candidate_id, "status": "VALID"}


def validate_promotion_batch(
    staging_repository: StagingRepositoryProtocol,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol,
    candidate_ids: list[str],
) -> dict[str, Any]:
    """Read-only. Never promotes, regardless of outcome.

    MWO-LTSA-RECOVERY-STATUS-LATENCY-001 -- batched, not one-query-per-
    candidate: N=540 previously meant ~1,624 individual round trips
    (find_by_id + find_by_source_reference + find_by_asset_and_date per
    candidate, each opening a fresh connection), measured at ~54s in
    production -- long enough to routinely exceed the frontend's default
    15s request timeout and leave the recovery/promotion status
    permanently unreachable. Now: exactly 3 batched queries total,
    regardless of N (find_by_ids, find_by_source_references,
    find_by_asset_dates), then pure in-memory classification
    (_classify_one) with byte-identical rules/ordering to before."""
    if not candidate_ids:
        raise EmptyBatchError("candidate_ids must not be empty")
    if len(candidate_ids) > MAX_PROMOTION_BATCH:
        raise BatchTooLargeError(f"{len(candidate_ids)} exceeds MAX_PROMOTION_BATCH={MAX_PROMOTION_BATCH}")
    seen: set[str] = set()
    duplicates = sorted({cid for cid in candidate_ids if cid in seen or seen.add(cid)})  # type: ignore[func-returns-value]
    if duplicates:
        raise DuplicateCandidateIdError(f"duplicate candidate_id(s) in request: {duplicates}")

    candidates_by_id = {
        c["document_field_extraction_id"]: c for c in staging_repository.find_by_ids(candidate_ids)
    }

    source_references = [f"document_field_extraction:{cid}" for cid in candidate_ids]
    already_by_source_reference = {
        r["source_reference"]: r for r in pm_occurrence_repository.find_by_source_references(source_references)
    }

    pairs: list[tuple[str, str]] = []
    for cid in candidate_ids:
        candidate = candidates_by_id.get(cid)
        if candidate is None:
            continue
        pump_tag = candidate.get("pump_tag_number")
        fields = candidate.get("reviewed_fields") or candidate.get("extracted_fields") or {}
        occurrence_date = fields.get("occurrence_date")
        if pump_tag and occurrence_date:
            pairs.append((pump_tag, occurrence_date))
    conflict_by_asset_date: dict[tuple[str, str], dict[str, Any]] = {}
    for row in pm_occurrence_repository.find_by_asset_dates(pairs):
        key = (row["asset_code"], row["occurrence_date"])
        conflict_by_asset_date.setdefault(key, row)

    results = [
        _classify_one(cid, candidates_by_id, already_by_source_reference, conflict_by_asset_date)
        for cid in candidate_ids
    ]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    # ALREADY_PROMOTED is a valid, safe-no-op outcome (exact retry after a
    # prior full success) -- only a genuinely ineligible/conflicting entry
    # blocks the batch.
    eligible = {"VALID", "ALREADY_PROMOTED"}
    all_valid = all(r["status"] in eligible for r in results)
    return {"results": results, "counts": counts, "all_valid": all_valid}


def promote_pm_batch(
    staging_repository: StagingRepositoryProtocol,
    pm_occurrence_repository: PMOccurrenceRepositoryProtocol,
    candidate_ids: list[str],
    *,
    pm_schedule_code: str,
    promoted_by: str,
) -> dict[str, Any]:
    """Fail-closed, true single-transaction exact-batch promotion.
    Validates every id first (read-only); if any is not VALID/ALREADY_
    PROMOTED, promotes NOTHING. If all pass, calls PMOccurrenceRepository.
    promote_historical_pm_batch_atomic() ONCE with every id -- Postgres's
    own implicit-transaction guarantee (same mechanism as stage_verified_
    batch()/bulk_review_batch_atomic()) makes the write all-or-nothing."""
    precheck = validate_promotion_batch(staging_repository, pm_occurrence_repository, candidate_ids)
    if not precheck["all_valid"]:
        return {"results": [], "precheck": precheck, "status": "REJECTED_PRECHECK_FAILED"}

    try:
        rows = pm_occurrence_repository.promote_historical_pm_batch_atomic(
            candidate_ids, pm_schedule_code=pm_schedule_code, promoted_by=promoted_by,
        )
    except Exception as error:  # noqa: BLE001 -- DB driver exception type varies; means the script's own DO block raised and Postgres rolled everything back
        return {"results": [], "precheck": precheck, "status": "REJECTED_ATOMIC_TRANSACTION_FAILED", "error": str(error)}
    if len(rows) != len(candidate_ids):
        raise PromotionBatchError(f"atomic batch promote returned {len(rows)} rows for {len(candidate_ids)} requested ids")
    return {"results": rows, "precheck": precheck, "status": "PROMOTED"}


__all__ = [
    "MAX_PROMOTION_BATCH",
    "PromotionBatchError",
    "BatchTooLargeError",
    "EmptyBatchError",
    "DuplicateCandidateIdError",
    "StagingRepositoryProtocol",
    "PMOccurrenceRepositoryProtocol",
    "validate_promotion_batch",
    "promote_pm_batch",
]
