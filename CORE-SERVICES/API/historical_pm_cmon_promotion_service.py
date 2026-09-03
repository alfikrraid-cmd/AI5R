"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- promotes a REVIEWED historical
PM/CMON staging candidate into the real canonical pm_occurrence /
condition_monitoring_reading tables.

Never promotes anything not REVIEWED (Phase 4/14's own "review before
promote" gate) and never promotes a candidate whose pump match was not
resolved to a real tag (pump_tag_number must be set on the staging row --
either by an EXACT_MATCH at extraction time or a human reviewer's
correction; Phase 6's "only EXACT_MATCH may be auto-suggested... human
review remains required before promotion").

Historical workflow-state honesty (Phase 11): every promoted record
starts life as a normal DRAFT, exactly like a live-created record --
this pipeline never fabricates submitted_by/reviewed_by/technical_
reviewed_by/JC approval. A historically-imported record only reaches
SUBMITTED/FINALIZED if a real human later drives it through the SAME
live PM/CMON review UI (PMOccurrenceDetailPanel.jsx /
ConditionMonitoringReadingDetailPanel.jsx) this session already built --
this promotion service's only job ends at DRAFT.

MWO-LTSA-ATOMIC-PM-PROMOTION-001 -- promote_pm_occurrence_candidate()
(the original PM promotion function) is REMOVED, not deprecated: it
performed create_draft() (INSERT pm_occurrence) and staging_repository.
mark_saved() (UPDATE document_field_extraction) as two separate,
non-transactional writes. A failure between them left a real
pm_occurrence row with its source candidate still REVIEWED; a retry
would not hit AlreadyPromotedError (candidate status was never SAVED)
and pm_occurrence carries no unique constraint on (asset_code,
occurrence_date) to catch the resulting duplicate. promote_pm_
occurrence_atomic() below replaces it: the insert and the SAVED
transition happen in ONE Postgres statement (pm_occurrence_repository.
promote_historical_pm_atomic()), so no partially-promoted state can
exist, and a retry is recognized (via pm_occurrence.source_reference,
an existing column/lookup, no schema change) as ALREADY_PROMOTED rather
than risking a duplicate.

promote_cmon_reading_candidate() (CMON) is UNCHANGED -- CMON recovery is
out of scope for this fix; it still performs create_draft() + the
optional mark_saved() as two separate writes, exactly as before.

Idempotency (Phase 15, CMON only now): the optional `staging_repository`
kwarg, when passed, transitions the candidate to SAVED (via
HistoricalPMCMONStagingRepository.mark_saved()) immediately after a
successful create_draft() -- so a second promotion attempt on the same
CMON candidate hits the AlreadyPromotedError gate above instead of
silently creating a second canonical record. mark_saved() is called
only AFTER create_draft() succeeds (never before), so a failed canonical
write leaves the candidate REVIEWED and still promotable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from condition_monitoring_reading_repository import ConditionMonitoringReadingRepository
    from historical_pm_cmon_staging_repository import HistoricalPMCMONStagingRepository
    from pm_occurrence_repository import PMOccurrenceRepository

PROVENANCE_HISTORICAL_IMPORT = "HISTORICAL_IMPORT"


class PromotionError(ValueError):
    pass


class AlreadyPromotedError(PromotionError):
    pass


def _source_reference(candidate_id: str) -> str:
    return f"document_field_extraction:{candidate_id}"


def promote_pm_occurrence_atomic(
    candidate_id: str,
    *,
    pm_occurrence_repository: "PMOccurrenceRepository",
    pm_schedule_code: str,
    promoted_by: str,
) -> dict:
    """Atomic, retry-safe replacement for the old promote_pm_occurrence_
    candidate(). Takes only `candidate_id` (not a pre-fetched candidate
    dict) -- pm_occurrence_repository.promote_historical_pm_atomic() does
    its own fresh, row-locked (FOR UPDATE) read of the candidate inside
    the same statement that inserts pm_occurrence and marks it SAVED, so
    there is no gap between "caller read the candidate" and "the write
    happens" for a concurrent promote of the same id to land in.
    `pm_schedule_code` is the same required, informal "UNSCHEDULED::
    <source>" reference as before (ltsa_hoc_pm_cm_upsert.py::
    build_unscheduled_reference)."""
    result = pm_occurrence_repository.promote_historical_pm_atomic(
        candidate_id, pm_schedule_code=pm_schedule_code, promoted_by=promoted_by,
    )
    if not result["candidate_found"]:
        raise PromotionError(f"candidate {candidate_id} not found")
    if result["already"] is not None:
        raise AlreadyPromotedError(candidate_id)
    if result["conflict"] is not None:
        conflict = result["conflict"]
        raise PromotionError(
            f"candidate {candidate_id} conflicts with existing pm_occurrence "
            f"{conflict['pm_occurrence_code']} for the same asset/date"
        )
    if not result["eligible"]:
        raise PromotionError(
            f"candidate {candidate_id} is not eligible for promotion "
            "(must be REVIEWED, HISTORICAL_PM_OCCURRENCE_CANDIDATE, a resolved pump, and a set occurrence_date)"
        )
    if result["inserted"] is None:
        raise PromotionError(
            f"candidate {candidate_id} failed a promotion precondition (unknown pump or missing pm_schedule)"
        )
    if not result["marked_saved"]:
        raise PromotionError(
            f"candidate {candidate_id} was promoted but the atomic statement did not mark it SAVED -- "
            "this should be unreachable (mark_saved is gated on the same insert); investigate"
        )
    return result["inserted"]


def promote_cmon_reading_candidate(
    candidate: dict,
    *,
    cmon_repository: "ConditionMonitoringReadingRepository",
    condition_monitoring_schedule_code: str,
    promoted_by: str,
    staging_repository: "HistoricalPMCMONStagingRepository | None" = None,
) -> dict:
    if candidate["status"] == "SAVED":
        raise AlreadyPromotedError(candidate["document_field_extraction_id"])
    if candidate["status"] != "REVIEWED":
        raise PromotionError(f"candidate {candidate['document_field_extraction_id']} is not REVIEWED (status={candidate['status']!r})")
    if not candidate.get("pump_tag_number"):
        raise PromotionError(
            f"candidate {candidate['document_field_extraction_id']} has no resolved pump_tag_number -- "
            "cannot promote an unmatched pump (Phase 6: only a real match may be promoted)"
        )

    fields = candidate.get("reviewed_fields") or candidate.get("extracted_fields") or {}
    measurements = {
        k: v for k, v in fields.items() if k not in ("reading_date", "asset_type", "finding")
    }
    record = cmon_repository.create_draft(
        condition_monitoring_schedule_code=condition_monitoring_schedule_code,
        asset_code=candidate["pump_tag_number"],
        asset_type=fields.get("asset_type", "PUMP"),
        reading_date=fields.get("reading_date"),
        measurements=measurements,
        created_by=promoted_by,
        provenance=PROVENANCE_HISTORICAL_IMPORT,
        source_reference=_source_reference(candidate["document_field_extraction_id"]),
        finding=fields.get("finding"),
    )
    if staging_repository is not None:
        staging_repository.mark_saved(candidate["document_field_extraction_id"])
    return record


__all__ = [
    "PROVENANCE_HISTORICAL_IMPORT",
    "PromotionError",
    "AlreadyPromotedError",
    "promote_pm_occurrence_atomic",
    "promote_cmon_reading_candidate",
]
