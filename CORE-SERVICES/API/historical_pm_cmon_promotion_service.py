"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- promotes a REVIEWED historical
PM/CMON staging candidate into the real canonical pm_occurrence /
condition_monitoring_reading tables.

The ONLY promotion path -- calls the exact same pm_occurrence_repository.
create_draft() / condition_monitoring_reading_repository.create_draft()
every other PM/CMON record (digitally created or historically imported)
goes through, with provenance='HISTORICAL_IMPORT' and source_reference
pointing back at the staging row (Phase 16: "which historical report
produced this record"). No parallel INSERT path is written here -- this
is deliberately the smallest possible promotion function, per this MWO's
own "reuse canonical architecture" instruction.

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

Idempotency (Phase 15): the optional `staging_repository` kwarg, when
passed, transitions the candidate to SAVED (via
HistoricalPMCMONStagingRepository.mark_saved()) immediately after a
successful create_draft() -- so a second promotion attempt on the same
candidate hits the AlreadyPromotedError gate above instead of silently
creating a second canonical record. mark_saved() is called only AFTER
create_draft() succeeds (never before), so a failed canonical write
leaves the candidate REVIEWED and still promotable -- the "candidate
remains reviewable if promotion fails" requirement. The kwarg is
optional (default None, matching every other additive kwarg in this
MWO) so a caller that only wants the canonical write, without touching
staging state, still can.
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


def promote_pm_occurrence_candidate(
    candidate: dict,
    *,
    pm_occurrence_repository: "PMOccurrenceRepository",
    pm_schedule_code: str,
    promoted_by: str,
    staging_repository: "HistoricalPMCMONStagingRepository | None" = None,
) -> dict:
    """`candidate` is a REVIEWED document_field_extraction row (as
    returned by HistoricalPMCMONStagingRepository). `pm_schedule_code` is
    a required, informal reference (pm_occurrence.pm_schedule_code is
    NOT NULL, no real Schedule exists for historical data) -- callers
    should pass the same self-disclosing "UNSCHEDULED::<source>" pattern
    ltsa_hoc_pm_cm_upsert.py::build_unscheduled_reference already
    established, reused here rather than inventing a second convention."""
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
    record = pm_occurrence_repository.create_draft(
        pm_schedule_code=pm_schedule_code,
        asset_code=candidate["pump_tag_number"],
        asset_type=fields.get("asset_type", "PUMP"),
        occurrence_date=fields.get("occurrence_date"),
        activities=fields.get("activities"),
        remarks=fields.get("remarks"),
        created_by=promoted_by,
        provenance=PROVENANCE_HISTORICAL_IMPORT,
        source_reference=_source_reference(candidate["document_field_extraction_id"]),
    )
    if staging_repository is not None:
        staging_repository.mark_saved(candidate["document_field_extraction_id"])
    return record


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
    "promote_pm_occurrence_candidate",
    "promote_cmon_reading_candidate",
]
