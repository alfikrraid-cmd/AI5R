"""MWO-LTSA-BULK-HISTORICAL-REVIEW-001 -- a SECOND, narrower "review" path
alongside the existing single-candidate historical_review.py router
actions (review/reject/promote unchanged -- still the only path for a
field correction, a pump-match resolution, a rejection, or a status
other than REVIEWED). This service only ever CONFIRMS-AS-EXTRACTED
(never corrects a field, never resolves an unmatched pump, never
rejects, never promotes) an explicit, caller-supplied candidate_id list,
restricted to PENDING_REVIEW PM candidates, in one atomic all-or-nothing
transaction -- for a human reviewer who has already verified an entire
recovery batch out-of-band and needs to confirm it in bulk rather than
clicking through hundreds of individually-identical "Confirm As
Extracted" actions.

Generic, not tied to any one batch size or manifest: MAX_BULK_REVIEW_
BATCH only bounds request size; the caller always supplies the exact
candidate_ids it wants reviewed -- this module never discovers or
selects a batch itself.
"""

from __future__ import annotations

from typing import Any, Protocol

MAX_BULK_REVIEW_BATCH = 1000
_ELIGIBLE_DOMAIN = "HISTORICAL_PM_OCCURRENCE_CANDIDATE"
_ELIGIBLE_STATUS = "PENDING_REVIEW"


class BulkReviewError(ValueError):
    pass


class BatchTooLargeError(BulkReviewError):
    pass


class EmptyBatchError(BulkReviewError):
    pass


class DuplicateCandidateIdError(BulkReviewError):
    pass


class StagingRepositoryProtocol(Protocol):
    def find_by_id(self, candidate_id: str) -> dict[str, Any] | None: ...
    def bulk_review_batch_atomic(self, candidate_ids: list[str], *, reviewed_by: str) -> list[dict[str, Any]]: ...


def _validate_one(repository: StagingRepositoryProtocol, candidate_id: str) -> dict[str, Any]:
    """Read-only. Never reviews."""
    candidate = repository.find_by_id(candidate_id)
    if candidate is None:
        return {"candidate_id": candidate_id, "status": "NOT_FOUND"}
    if candidate.get("detected_document_type") != _ELIGIBLE_DOMAIN:
        return {"candidate_id": candidate_id, "status": "WRONG_DOMAIN"}
    if candidate.get("status") != _ELIGIBLE_STATUS:
        return {"candidate_id": candidate_id, "status": "WRONG_STATUS"}
    return {"candidate_id": candidate_id, "status": "VALID"}


def validate_request_shape(candidate_ids: list[str]) -> None:
    """Read-only, no repository access -- pure request-shape checks
    (empty, oversized, duplicate ids). Split out from validate_bulk_
    review_batch so a caller (the router) can reject a malformed
    request cheaply, before spending one find_by_id + scope check per
    id on a batch that was never going to be valid."""
    if not candidate_ids:
        raise EmptyBatchError("candidate_ids must not be empty")
    if len(candidate_ids) > MAX_BULK_REVIEW_BATCH:
        raise BatchTooLargeError(f"{len(candidate_ids)} exceeds MAX_BULK_REVIEW_BATCH={MAX_BULK_REVIEW_BATCH}")
    seen: set[str] = set()
    duplicates = sorted({cid for cid in candidate_ids if cid in seen or seen.add(cid)})  # type: ignore[func-returns-value]
    if duplicates:
        raise DuplicateCandidateIdError(f"duplicate candidate_id(s) in request: {duplicates}")


def validate_bulk_review_batch(repository: StagingRepositoryProtocol, candidate_ids: list[str]) -> dict[str, Any]:
    """Read-only. Never reviews, regardless of outcome. Raises for a
    malformed request (empty, oversized, duplicate ids) rather than
    reporting those as per-row statuses -- those are request-shape
    errors, not candidate-eligibility outcomes."""
    validate_request_shape(candidate_ids)

    results = [_validate_one(repository, cid) for cid in candidate_ids]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"results": results, "counts": counts, "all_valid": counts.get("VALID", 0) == len(results)}


def bulk_review_candidates(
    repository: StagingRepositoryProtocol, candidate_ids: list[str], *, reviewed_by: str
) -> dict[str, Any]:
    """Fail-closed, true single-transaction bulk confirm-as-extracted.
    Validates every id first (read-only); if any is not VALID, reviews
    NOTHING. If all are VALID, calls repository.bulk_review_batch_atomic()
    ONCE with every id -- Postgres's own implicit-transaction guarantee
    (same mechanism as historical_selective_staging_service.
    stage_verified_candidates()) makes the actual write all-or-nothing."""
    precheck = validate_bulk_review_batch(repository, candidate_ids)
    if not precheck["all_valid"]:
        return {"reviewed": [], "precheck": precheck, "status": "REJECTED_PRECHECK_FAILED"}

    try:
        reviewed = repository.bulk_review_batch_atomic(candidate_ids, reviewed_by=reviewed_by)
    except Exception as error:  # noqa: BLE001 -- DB driver exception type varies; means the script's own DO block raised and Postgres rolled everything back
        return {"reviewed": [], "precheck": precheck, "status": "REJECTED_ATOMIC_TRANSACTION_FAILED", "error": str(error)}
    if len(reviewed) != len(candidate_ids):
        raise BulkReviewError(f"atomic bulk review returned {len(reviewed)} rows for {len(candidate_ids)} requested ids")
    return {"reviewed": reviewed, "precheck": precheck, "status": "REVIEWED"}


__all__ = [
    "MAX_BULK_REVIEW_BATCH",
    "BulkReviewError",
    "BatchTooLargeError",
    "EmptyBatchError",
    "DuplicateCandidateIdError",
    "StagingRepositoryProtocol",
    "validate_request_shape",
    "validate_bulk_review_batch",
    "bulk_review_candidates",
]
