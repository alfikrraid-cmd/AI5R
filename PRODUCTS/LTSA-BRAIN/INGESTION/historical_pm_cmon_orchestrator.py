"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- orchestrates one historical
monthly area report (PDF + matching XLSX) through:

  source registration (hash, immutability) -> XLSX projection (reusing
  ltsa_hoc_pm_cm_ingestion.py's own proven functions, unmodified) ->
  duplicate classification -> pump matching -> area/MA resolution ->
  document classification -> staged candidates (via
  historical_pm_cmon_staging_repository.py) OR a pure, zero-write DRY RUN
  report (Phase 22).

No canonical PM/CMON write happens here -- staging only. Promotion is a
separate, later, explicitly human-gated step
(historical_pm_cmon_promotion_service.py).

Findings (Phase 9): a Finding-sheet row is staged as its own
HISTORICAL_FINDING_CANDIDATE, never auto-merged into a CMON reading
candidate's `finding` field. The real Finding sheet carries no per-row
reading date, and every real July pump tag has MULTIPLE CM Measuring
Report readings within the same monthly report (proven this session --
every single distinct tag across all 4 areas has more than one dated
reading), so there is no safe, non-fabricated way to auto-pick which
specific dated reading a finding's remarks belong to. Attachment (via the
existing condition_monitoring_reading_repository.update_draft(finding=
...) path once a specific reading is chosen) is left to a human reviewer,
never guessed by this pipeline.

Note: ltsa_hoc_pm_cm_ingestion.py's own project_finding_rows()/
_derive_finding_dates() are NOT used here (unlike the CM/PM projections)
-- proven this session to be calibrated for a different, older 3-column
workbook and incompatible with the real July "Findings"/"FINDINGS"
sheets (see historical_pm_cmon_extraction.py's own module docstring for
the full finding). extract_finding_candidates_from_workbook() in that
same module is used instead.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import openpyxl  # noqa: E402
from ltsa_hoc_pm_cm_ingestion import (  # noqa: E402
    _CM_SHEET,
    _PM_SHEET,
    project_cm_reading_rows,
    project_pm_occurrence_rows,
)
from ltsa_hoc_pm_cm_upsert import (  # noqa: E402
    build_condition_monitoring_reading_code,
    build_pm_occurrence_code,
)
from ltsa_pump_inventory_ingestion import _sheet_rows  # noqa: E402
from historical_pm_cmon_extraction import (  # noqa: E402
    classify_document,
    classify_source_duplicate,
    extract_finding_candidates_from_workbook,
    match_pump_tag,
    resolve_area,
    sha256_file,
)

# Candidate Finding sheet names actually observed across the real July
# reports this session (case/spelling genuinely differs per area --
# "Findings" (HOC/HCC/OM_UTL) vs "FINDINGS" (HSC) -- never assumed to be
# the older workbook's own "finnding" typo).
_FINDING_SHEET_CANDIDATES = ("Findings", "FINDINGS", "finnding", "Finding")


def _resolve_finding_sheet_name(workbook_path: Path) -> str | None:
    wb = openpyxl.load_workbook(workbook_path, read_only=True)
    try:
        names = set(wb.sheetnames)
    finally:
        wb.close()
    for candidate in _FINDING_SHEET_CANDIDATES:
        if candidate in names:
            return candidate
    return None


@dataclass(frozen=True, slots=True)
class SourceDocumentInfo:
    area_label: str
    pdf_path: Path
    xlsx_path: Path
    pdf_sha256: str
    xlsx_sha256: str


@dataclass(slots=True)
class CandidateSummary:
    kind: str  # "PM" | "CMON"
    code: str  # deterministic LTSA-PMO-.../LTSA-CMONR-... identity
    tag_number: str | None  # raw, as-extracted tag -- NEVER used as a canonical relation
    pump_match: str  # EXACT_MATCH / REVIEW_REQUIRED / NO_MATCH
    area: dict[str, Any]
    fields: dict[str, Any]
    source_page_hint: int | None = None
    # MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001 -- the CANONICAL
    # roster form match_pump_tag() actually resolved to (e.g. tag_number=
    # '200 - P - 1A', matched_tag='200-P-1A' after whitespace
    # normalization), populated ONLY when pump_match == EXACT_MATCH.
    # tag_number and matched_tag are deliberately never conflated: staging
    # must set pump_tag_number from matched_tag (the real ltsa_pumps FK
    # target), never from the raw tag_number, or a whitespace-normalized
    # match would violate document_field_extraction's own FK constraint.
    matched_tag: str | None = None


@dataclass(slots=True)
class AreaDryRunResult:
    area_label: str
    source: SourceDocumentInfo
    document_classification: str
    pm_candidates: list[CandidateSummary] = field(default_factory=list)
    cmon_candidates: list[CandidateSummary] = field(default_factory=list)
    finding_candidates: list[CandidateSummary] = field(default_factory=list)
    critical_missing: list[str] = field(default_factory=list)


def register_source_document(pdf_path: Path, xlsx_path: Path, *, area_label: str) -> SourceDocumentInfo:
    return SourceDocumentInfo(
        area_label=area_label,
        pdf_path=pdf_path,
        xlsx_path=xlsx_path,
        pdf_sha256=sha256_file(pdf_path),
        xlsx_sha256=sha256_file(xlsx_path),
    )


def build_area_dry_run(
    source: SourceDocumentInfo,
    *,
    canonical_pump_tags: set[str],
    known_source_hashes: set[str] = frozenset(),
) -> AreaDryRunResult:
    """Zero-write: reads the XLSX only, classifies, matches -- never opens
    a database connection, never mutates canonical PM/CMON tables."""
    duplicate_status = classify_source_duplicate(source.xlsx_sha256, known_hashes=known_source_hashes)

    cm_rows = project_cm_reading_rows(_sheet_rows(source.xlsx_path, _CM_SHEET))
    pm_rows = project_pm_occurrence_rows(_sheet_rows(source.xlsx_path, _PM_SHEET))

    finding_sheet_name = _resolve_finding_sheet_name(source.xlsx_path)
    finding_candidates_raw = []
    if finding_sheet_name:
        finding_candidates_raw = extract_finding_candidates_from_workbook(
            _sheet_rows(source.xlsx_path, finding_sheet_name), sheet_name=finding_sheet_name
        )

    result = AreaDryRunResult(
        area_label=source.area_label,
        source=source,
        document_classification=classify_document(len(pm_rows), len(cm_rows)),
    )
    if duplicate_status != "NEW_SOURCE":
        result.critical_missing.append(f"source duplicate_status={duplicate_status} -- not staged")
        return result

    for row in pm_rows:
        match = match_pump_tag(row["tag_number"], canonical_pump_tags)
        code = build_pm_occurrence_code(row["source_sheet_name"], row["source_row_number"])
        area_info = resolve_area(row.get("area"), row.get("location"))
        result.pm_candidates.append(
            CandidateSummary(
                kind="PM",
                code=code,
                tag_number=row["tag_number"],
                pump_match=match.outcome,
                matched_tag=match.matched_tag,
                area={
                    "source_area": area_info.source_area,
                    "source_location": area_info.source_location,
                    "normalized_ma": area_info.normalized_ma,
                    "mapping_basis": area_info.mapping_basis,
                },
                fields={
                    "occurrence_date": row["occurrence_date"],
                    "api_plan": row["api_plan"],
                    "status": row["status"],
                    "activities": [
                        {"description": label, "done": True} for label in row["checklist_completion"]
                    ],
                    "asset_type": "PUMP",
                },
                source_page_hint=None,
            )
        )
        if area_info.mapping_basis == "REVIEW_REQUIRED":
            result.critical_missing.append(f"PM {code}: Area/MA REVIEW_REQUIRED for tag {row['tag_number']}")
        if match.outcome != "EXACT_MATCH":
            result.critical_missing.append(f"PM {code}: pump match {match.outcome} for tag {row['tag_number']!r}")

    for row in cm_rows:
        match = match_pump_tag(row["tag_number"], canonical_pump_tags)
        code = build_condition_monitoring_reading_code(row["source_sheet_name"], row["source_row_number"])
        measurement_fields = {
            k: v for k, v in row.items()
            if k not in ("source_sheet_name", "source_row_number", "tag_number", "reading_date", "api_plan")
        }
        measurement_fields["reading_date"] = row["reading_date"]
        measurement_fields["asset_type"] = "PUMP"
        result.cmon_candidates.append(
            CandidateSummary(
                kind="CMON",
                code=code,
                tag_number=row["tag_number"],
                pump_match=match.outcome,
                matched_tag=match.matched_tag,
                area={},  # CM Measuring Report rows carry no per-row Area/MA column in the source
                fields=measurement_fields,
            )
        )
        if match.outcome != "EXACT_MATCH":
            result.critical_missing.append(f"CMON {code}: pump match {match.outcome} for tag {row['tag_number']!r}")

    # Findings are staged as their OWN candidates (HISTORICAL_FINDING_
    # CANDIDATE) -- never auto-merged onto a specific CMON reading. See
    # this module's own header docstring: the Finding sheet has no
    # per-row reading date, and every real tag has multiple dated CM
    # readings per report, so which reading a finding belongs to is a
    # human-review decision, never guessed here.
    for f in finding_candidates_raw:
        match = match_pump_tag(f.tag_number, canonical_pump_tags)
        code = f"LTSA-FINDING-{f.source_sheet_name}-{f.source_row_number}"
        result.finding_candidates.append(
            CandidateSummary(
                kind="FINDING",
                code=code,
                tag_number=f.tag_number,
                pump_match=match.outcome,
                matched_tag=match.matched_tag,
                area={"source_location": f.source_location},
                fields={
                    "api_plan": f.api_plan,
                    "pump_type": f.pump_type,
                    "seal_leakage_de": f.seal_leakage_de,
                    "seal_leakage_nde": f.seal_leakage_nde,
                    "remarks": f.remarks,
                    "follow_up_date_raw": f.follow_up_date_raw,
                },
            )
        )
        if match.outcome != "EXACT_MATCH":
            result.critical_missing.append(f"FINDING {code}: pump match {match.outcome} for tag {f.tag_number!r}")

    if finding_sheet_name is None:
        result.critical_missing.append("no Finding sheet found in workbook (checked known sheet name variants)")

    return result


# ---------------------------------------------------------------------------
# Staging bridge (MWO-LTSA-HISTORICAL-INCOMPLETE-DATA-POLICY-001) -- turns
# a build_area_dry_run() result into real document_field_extraction rows.
# This is the FIRST code path in the pipeline that actually calls
# HistoricalPMCMONStagingRepository.create_candidate() -- build_area_dry_
# run() itself stays pure/zero-write, per its own docstring.
#
# Pump Tag Rule (this MWO's own Core Model): pump_tag_number is set ONLY
# when the deterministic matcher found EXACT_MATCH, and ONLY to the
# resolved CANONICAL form (candidate.matched_tag) -- never the raw
# tag_number. This distinction is load-bearing, not cosmetic: real real
# July data proved this session that a whitespace-normalized EXACT_MATCH
# (e.g. raw '211 - P - 1A' -> canonical '211-P-1A') would violate
# document_field_extraction's own real FK constraint on pump_tag_number
# if the raw form were used -- ltsa_pumps only ever contains the
# canonical spelling. REVIEW_REQUIRED and NO_MATCH both stage with
# pump_tag_number=NULL, never the raw tag substituted in as if it were
# resolved (that would silently assert an unproven pump relation). The
# raw, as-extracted tag is NEVER discarded either way -- it is preserved
# verbatim in extracted_fields["raw_asset_tag"], so a NULL
# pump_tag_number never means "the tag is unknown", only "the canonical
# relation is unresolved". A motor tag (e.g. 701-MM-51) is never
# converted to a pump tag by this or any upstream step -- it simply
# stages as an INCOMPLETE observation with its own real tag preserved.
def stage_area_candidates(
    result: AreaDryRunResult,
    *,
    staging_repository,
    source_document_id: str,
) -> list[dict]:
    staged: list[dict] = []
    for candidate in result.pm_candidates + result.cmon_candidates + result.finding_candidates:
        detected_type = {
            "PM": "HISTORICAL_PM_OCCURRENCE_CANDIDATE",
            "CMON": "HISTORICAL_CMON_READING_CANDIDATE",
            "FINDING": "HISTORICAL_FINDING_CANDIDATE",
        }[candidate.kind]
        pump_tag_number = candidate.matched_tag if candidate.pump_match == "EXACT_MATCH" else None
        fields = dict(candidate.fields)
        fields["raw_asset_tag"] = candidate.tag_number
        row = staging_repository.create_candidate(
            source_document_id=source_document_id,
            detected_document_type=detected_type,
            extracted_fields=fields,
            pump_tag_number=pump_tag_number,
            source_page=candidate.source_page_hint,
        )
        staged.append(row)
    return staged


__all__ = [
    "SourceDocumentInfo",
    "CandidateSummary",
    "AreaDryRunResult",
    "register_source_document",
    "build_area_dry_run",
    "stage_area_candidates",
]
