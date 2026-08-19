"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- pure extraction, classification,
and matching logic for historical monthly "Laporan PM, CM & Pemasangan Seal"
reports (John Crane / PT Tommy Adji Prasetyo / Pertamina RU II Dumai).

IMPORTANT -- extraction-path status: each area report exists as a matched
PDF+XLSX pair. Discovered this session: an existing, already-tested module
(ltsa_hoc_pm_cm_ingestion.py, built for a prior HOC-specific MWO) already
projects the SAME "CM Measuring Report"/" PM Mech Seal" sheets out of the
XLSX file, and its output was cross-validated this session against this
module's own PDF extraction for the real HOC July report -- byte-for-byte
identical row counts and values. XLSX cell reads are inherently more
reliable than PDF table-geometry parsing (no OCR/layout guessing at all),
so historical_pm_cmon_orchestrator.py uses THAT existing module
(project_cm_reading_rows/project_pm_occurrence_rows, reused unmodified) as
the PRIMARY extraction path for CM Measuring / PM Mechseal staging
candidates
-- per this MWO's own "reuse canonical architecture, do not build a second
generic ingestion engine" instruction. The PDF-table functions below
(extract_cm_measuring_candidates/extract_pm_mechseal_candidates/
extract_finding_candidates) are kept as an independent, already-proven
cross-validation utility (and as the only path when a report has no
matching XLSX) -- not the primary pipeline for those two tables.

Finding extraction is the ONE exception: that same module's
project_finding_rows()/_derive_finding_dates() were calibrated for a
different, older 3-column (date/tag/text) workbook and were PROVEN
incompatible with the real July "Findings"/"FINDINGS" sheets during this
session's own real dry run -- against real data they silently misread the
API PLAN column as the finding text and leaked header rows through as
fake candidate rows (tag_number="TAG NO."). They are NOT reused for
Finding. This module's own extract_finding_candidates_from_workbook()
(XLSX-native, see its docstring below) is the primary Finding extraction
path instead; extract_finding_candidates() (PDF-table based, below)
remains the cross-validation utility / no-XLSX fallback for Finding too.

Also discovered and deliberately NOT reused: ltsa_hoc_pm_cm_upsert.py's
own plan_import() routes Finding rows into cm_report (Corrective
Maintenance) with a fabricated failure_category -- a real semantic
collision with this MWO's own Semantic Freeze (cm_report remains
Corrective Maintenance; CM Measuring Report data targets
condition_monitoring_reading only), left over from before the Chief
Architect's mid-session domain correction. This pipeline never calls
that function and never writes cm_report.

This module NEVER writes to a database and NEVER touches production. It
turns one source PDF into typed, honestly-null candidate records plus a
duplicate/pump-match verdict. Promotion into the real canonical
pm_occurrence/condition_monitoring_reading tables is a separate, later step
(see historical_pm_cmon_staging_repository.py /
historical_pm_cmon_promotion_service.py) -- this MWO's own Golden Rule:
"Do NOT directly insert extracted values into production canonical tables
without review."

Table-column provenance (verified against the REAL source PDFs this
session, via pdfplumber's structured extract_tables() -- NOT the raw text
stream, which was independently proven unreliable for this dense
positional layout: a first-pass manual reading of the raw text stream
mis-attributed which numbers belonged to which measurement column; only
the bordered-table geometry pdfplumber uses gives a trustworthy column
index):

  CM Measuring Report table, 24 columns (0-indexed):
    0 No, 1 Date, 2 Tag Number, 3 API PLAN,
    4/5 Flushing DE/NDE, 6/7 Quench DE/NDE,
    8/9 Flushing In (LBI) DE/NDE, 10/11 Flushing Out (LBO) DE/NDE,
    12/13 Cooling Water In DE/NDE, 14/15 Cooling Water Out DE/NDE,
    16/17 Mechseal Temp DE/NDE, 18/19 Mechanical Seal Leak (Y/N) DE/NDE,
    20/21 Water Jacket DE/NDE, 22 Suction (single), 23 Discharge (single).
  This maps 1:1 onto conditionMonitoringMeasurementFields.js's own field
  list (MWO-LTSA-PM-CMON-FOUNDATION-CLEANUP-001) -- confirmed empirically
  against real data, not assumed. The source has NO columns for the
  migration-014 fields (suction/discharge pressure, quench pressure,
  stuffing box/seal gland temp, vibration, motor current) -- those stay
  NULL for this source format, never fabricated merely because the
  canonical schema supports them (Phase 8's own explicit instruction).

  PM Mechseal table: NO, DATE, TAG NUMBER, AREA (e.g. "MA-1"), LOCATION
  (e.g. "HOC"), API PLAN, STATUS, then N checklist-item columns, each
  headed by its own real item CODE (e.g. "1"=Flushing Line, "4"=Quench
  Line, "19"=Strainer, "17"=Check Valve DE Side, "18"=Check Valve NDE
  Side, "6"=Reservoir, "8"=Cooling Water Cooler -- the same 7-item subset
  CreatePMOccurrenceModal.jsx's own ACTIVITY_OPTIONS already uses,
  confirmed to share the exact same numbering scheme as the real source).
  The column HEADER TEXT itself is rotated 90 degrees in the PDF and
  extracts as garbled, unreliable character soup -- only the numeric item-
  CODE row is used for column identity; a full code->description catalog
  is not established here for codes this module has no other evidence
  for (never fabricated).

  Finding table: NO, AREA (location code, e.g. "DCU"/"HVU"), TAG NO.,
  API PLAN, PUMP TYPE, SEAL LEAKAGE DE/NDE, FLUSHING DE/NDE,
  QUENCHING DE/NDE, REMARKS (free-text finding), a trailing date column.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

import pdfplumber

# ---------------------------------------------------------------------------
# Hashing (Phase 3) -- reuses the exact SHA-256/chunked convention already
# established, unwired, at AI5R-SDK/FOUNDATION/file_hash_service.py. Kept
# as a free function here (not importing that module) only because this
# file must remain importable from the disposable-Postgres CLI scripts
# this MWO's own dry-run/tests run from, without adding an AI5R-SDK
# import-path dependency to a PRODUCTS/LTSA-BRAIN/INGESTION module; the
# algorithm and chunk size are identical.
# ---------------------------------------------------------------------------


def sha256_file(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Duplicate classification (Phase 3)
# ---------------------------------------------------------------------------

DuplicateStatus = Literal["EXACT_DUPLICATE", "POSSIBLE_DUPLICATE", "NEW_SOURCE"]


def classify_source_duplicate(
    source_hash: str,
    *,
    known_hashes: set[str],
    known_possible_duplicates: set[tuple[str, str, str]] = frozenset(),
    candidate_key: tuple[str, str, str] | None = None,
) -> DuplicateStatus:
    """`known_hashes` = every already-registered source document's exact
    SHA-256. `candidate_key`/`known_possible_duplicates` = an optional
    (asset_code, event_date, report_type) triple for the softer
    "looks like it might already exist" check Phase 3 allows (pump +
    report date + report type + source filename + existing occurrence/
    reading) -- deliberately NEVER auto-merged, only flagged."""
    if source_hash in known_hashes:
        return "EXACT_DUPLICATE"
    if candidate_key is not None and candidate_key in known_possible_duplicates:
        return "POSSIBLE_DUPLICATE"
    return "NEW_SOURCE"


# ---------------------------------------------------------------------------
# Pump identity matching (Phase 6) -- deliberately the SAME three-outcome
# shape installation_review_service.match_pump/MatchOutcome already
# establishes (MATCHED/AMBIGUOUS/NOT_FOUND), renamed to this MWO's own
# vocabulary. Exact string match only -- suffixes (A/B/AR/BR/C/D/...) are
# never stripped, sister pumps are never inferred equal.
# ---------------------------------------------------------------------------

PumpMatchOutcome = Literal["EXACT_MATCH", "REVIEW_REQUIRED", "NO_MATCH"]


@dataclass(frozen=True, slots=True)
class PumpMatchResult:
    outcome: PumpMatchOutcome
    extracted_tag: str
    matched_tag: str | None = None


def _collapse_whitespace(tag: str) -> str:
    """Removes spaces the source workbook inserted around hyphens (e.g.
    real HSC CM Measuring Report rows print '200 - P - 1A' while HSC's own
    Schedule/roster prints '200-P-1A') -- pure typography, not part of the
    tag's identity (unlike a suffix letter, which IS identity-bearing and
    is never touched here)."""
    return re.sub(r"\s+", "", tag)


def match_pump_tag(extracted_tag: str, canonical_tags: set[str]) -> PumpMatchResult:
    tag = (extracted_tag or "").strip()
    if not tag:
        return PumpMatchResult(outcome="NO_MATCH", extracted_tag=extracted_tag)
    if tag in canonical_tags:
        return PumpMatchResult(outcome="EXACT_MATCH", extracted_tag=tag, matched_tag=tag)

    # A whitespace-only variant (same characters, different spacing) is
    # strong evidence of the same physical tag -- but per Phase 6 ("human
    # review remains required before promotion") it is still surfaced for
    # confirmation, never silently promoted to EXACT_MATCH.
    collapsed = _collapse_whitespace(tag)
    whitespace_matches = {t for t in canonical_tags if _collapse_whitespace(t) == collapsed}
    if len(whitespace_matches) == 1:
        (only_match,) = whitespace_matches
        return PumpMatchResult(outcome="REVIEW_REQUIRED", extracted_tag=tag, matched_tag=only_match)

    # A near-miss (same digits, different/missing suffix) is exactly the
    # case that must NEVER be auto-resolved -- flagged for human review,
    # never silently matched.
    base = re.sub(r"[A-Z]+$", "", collapsed)
    near_misses = {t for t in canonical_tags if re.sub(r"[A-Z]+$", "", _collapse_whitespace(t)) == base}
    if near_misses:
        return PumpMatchResult(outcome="REVIEW_REQUIRED", extracted_tag=tag)
    return PumpMatchResult(outcome="NO_MATCH", extracted_tag=tag)


# ---------------------------------------------------------------------------
# Area / MA normalization (Phase 10) -- normalizes ONLY against the
# established canonical business mapping; never derives Contract from MA
# (UTL=MA-3 and OM=MA-4 remain distinct even though both belong to one
# combined report/contract, per this MWO's own explicit business context).
# ---------------------------------------------------------------------------

# Business-owner-established mapping (this MWO's own IMPORTANT BUSINESS
# CONTEXT section) -- normalized_area is DERIVED from source_area only
# when source_area is one of these exact, explicit strings; anything else
# is left unresolved, never guessed.
_MA_BY_LOCATION = {
    "HOC": "MA-1",
    "HSC & S. Pakning": "MA-2",
    "HSC": "MA-2",
    "S. PAKNING": "MA-2",
    "SPK": "MA-2",
    "HCC": "MA-2",
    "UTL": "MA-3",
    "OM": "MA-4",
}


@dataclass(frozen=True, slots=True)
class AreaResolution:
    source_area: str | None  # e.g. "MA-1", as literally printed in the source
    source_location: str | None  # e.g. "HOC", as literally printed in the source
    normalized_ma: str | None
    mapping_basis: Literal["EXPLICIT_SOURCE_MA", "LOCATION_LOOKUP", "REVIEW_REQUIRED"]


def resolve_area(source_area: str | None, source_location: str | None) -> AreaResolution:
    area = (source_area or "").strip() or None
    location = (source_location or "").strip() or None

    # The source's own "AREA" column (e.g. "MA-1") is the strongest
    # evidence -- when present, trust it verbatim, never re-derive.
    if area:
        return AreaResolution(area, location, area, "EXPLICIT_SOURCE_MA")

    # No explicit MA column this row -- fall back to a known location
    # name ONLY if it is an exact, unambiguous match to the established
    # mapping. Never inferred from a pump-number pattern.
    if location and location.upper() in {k.upper() for k in _MA_BY_LOCATION}:
        matched_key = next(k for k in _MA_BY_LOCATION if k.upper() == location.upper())
        return AreaResolution(area, location, _MA_BY_LOCATION[matched_key], "LOCATION_LOOKUP")

    return AreaResolution(area, location, None, "REVIEW_REQUIRED")


# ---------------------------------------------------------------------------
# CM Measuring Report extraction
# ---------------------------------------------------------------------------

# Column index -> (canonical snake_case column, unit). Matches
# conditionMonitoringMeasurementFields.js's MEASUREMENT_PAIR_FIELDS/
# MEASUREMENT_SINGLE_FIELDS exactly (frontend and this extractor share the
# same canonical field list, verified this session).
_CM_MEASURING_COLUMNS = [
    None, "date", "tag_number", "api_plan",
    "flushing_temp_de", "flushing_temp_nde",
    "quench_temp_de", "quench_temp_nde",
    "flushing_in_temp_de", "flushing_in_temp_nde",
    "flushing_out_temp_de", "flushing_out_temp_nde",
    "cooling_water_in_temp_de", "cooling_water_in_temp_nde",
    "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
    "mechseal_temp_de", "mechseal_temp_nde",
    "mechanical_seal_leak_de", "mechanical_seal_leak_nde",
    "water_jacket_temp_de", "water_jacket_temp_nde",
    "suction_temp", "discharge_temp",
]
_NUMERIC_CM_COLUMNS = {
    c for c in _CM_MEASURING_COLUMNS
    if c not in (None, "date", "tag_number", "api_plan", "mechanical_seal_leak_de", "mechanical_seal_leak_nde")
}


def _parse_numeric_cell(raw: str | None) -> float | None:
    """Blank stays None (missing/not recorded). An explicit 0 is preserved
    as 0.0, never coerced to None -- Phase 8/20's own hard requirement."""
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None  # Unparseable text (e.g. a stray note) -- honestly unresolved, not fabricated.


def _parse_leak_cell(raw: str | None) -> bool | None:
    """Y/N -> True/False; blank stays None (unknown), NEVER inferred as
    'N' (no leak) from an empty cell -- Phase 20's own explicit
    prohibition on inferring NO LEAK from a blank field."""
    if raw is None:
        return None
    text = raw.strip().upper()
    if text == "Y":
        return True
    if text == "N":
        return False
    return None


@dataclass(frozen=True, slots=True)
class CMONReadingCandidate:
    source_row_number: str | None
    reading_date: str | None  # as printed, e.g. "01-Jul-26" -- normalization is a review-time concern, not fabricated here
    tag_number: str | None
    api_plan: str | None
    measurements: dict[str, float | bool | None] = field(default_factory=dict)
    source_page: int | None = None
    raw_row: tuple[str | None, ...] = field(default_factory=tuple)


def extract_cm_measuring_candidates(pdf_path: str | Path, page_range: tuple[int, int]) -> list[CMONReadingCandidate]:
    """page_range is 1-indexed, inclusive, e.g. (42, 48). Returns one
    candidate per real data row (rows whose first cell is a row-number
    integer -- header/title rows are skipped)."""
    start, end = page_range
    candidates: list[CMONReadingCandidate] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index in range(start - 1, end):
            page = pdf.pages[page_index]
            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0] or not str(row[0]).strip().isdigit():
                        continue
                    measurements: dict[str, float | bool | None] = {}
                    for col_index, col_name in enumerate(_CM_MEASURING_COLUMNS):
                        if col_name in (None, "date", "tag_number", "api_plan"):
                            continue
                        cell = row[col_index] if col_index < len(row) else None
                        if col_name in ("mechanical_seal_leak_de", "mechanical_seal_leak_nde"):
                            measurements[col_name] = _parse_leak_cell(cell)
                        else:
                            measurements[col_name] = _parse_numeric_cell(cell)
                    candidates.append(
                        CMONReadingCandidate(
                            source_row_number=(row[0] or "").strip() or None,
                            reading_date=(row[1] or "").strip() or None if len(row) > 1 else None,
                            tag_number=(row[2] or "").strip() or None if len(row) > 2 else None,
                            api_plan=(row[3] or "").strip() or None if len(row) > 3 else None,
                            measurements=measurements,
                            source_page=page_index + 1,
                            raw_row=tuple(row),
                        )
                    )
    return candidates


# ---------------------------------------------------------------------------
# PM Mechseal (checklist / occurrence) extraction
# ---------------------------------------------------------------------------

# Only the item codes this session has real, disclosed evidence for
# (CreatePMOccurrenceModal.jsx's own ACTIVITY_OPTIONS, itself sourced from
# the December 2022 golden report per migration 014's own header). Any
# other code observed in a real source row is preserved honestly by its
# raw code, never given an invented description.
_KNOWN_ACTIVITY_LABELS = {
    "1": "Flushing Line",
    "4": "Quench Line",
    "19": "Strainer",
    "17": "Check Valve DE Side",
    "18": "Check Valve NDE Side",
    "6": "Reservoir",
    "8": "Cooling Water Cooler",
}


@dataclass(frozen=True, slots=True)
class PMOccurrenceCandidate:
    source_row_number: str | None
    occurrence_date: str | None
    tag_number: str | None
    source_area: str | None  # e.g. "MA-1", verbatim
    source_location: str | None  # e.g. "HOC", verbatim
    api_plan: str | None
    status: str | None  # e.g. "DONE", verbatim
    activities: list[dict[str, Any]] = field(default_factory=list)
    source_page: int | None = None
    raw_row: tuple[str | None, ...] = field(default_factory=tuple)


def extract_pm_mechseal_candidates(
    pdf_path: str | Path, page_range: tuple[int, int]
) -> list[PMOccurrenceCandidate]:
    """The checklist-item header row (numeric codes, e.g. "1","4","19",...)
    is auto-detected as the row immediately preceding the first real data
    row on each page -- the rotated/garbled text-label row above it is
    never parsed for identity, only for a human-readable hint where a
    known code maps to one (see _KNOWN_ACTIVITY_LABELS)."""
    start, end = page_range
    candidates: list[PMOccurrenceCandidate] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index in range(start - 1, end):
            page = pdf.pages[page_index]
            for table in page.extract_tables():
                item_codes: list[str | None] = []
                for row in table:
                    if not row:
                        continue
                    first = (row[0] or "").strip()
                    if not first.isdigit():
                        # The item-CODE header row (e.g. "1","4","19",...)
                        # and the "Total Accessories Cleaned (N Item)"
                        # totals row both have an all-numeric tail from
                        # column 7 onward -- indistinguishable by that
                        # signal alone. The real distinguishing fact
                        # (verified against the actual source table): the
                        # item-code row's own leading cells (0-6) are all
                        # blank, while the totals row's first cell is the
                        # literal descriptive text "Total Accessories
                        # Cleaned...". Only a blank-leading row may become
                        # item_codes, so the totals row is never mistaken
                        # for it.
                        if row[0] and row[0].strip():
                            continue
                        tail = [c for c in row[7:] if c and c.strip()]
                        if tail and all(c.strip().isdigit() for c in tail):
                            item_codes = row
                        continue

                    activities = []
                    for col_index in range(7, len(row)):
                        code = (item_codes[col_index].strip() if col_index < len(item_codes) and item_codes[col_index] else None)
                        if not code:
                            continue
                        marker = (row[col_index] or "").strip()
                        activities.append(
                            {
                                "code": code,
                                "description": _KNOWN_ACTIVITY_LABELS.get(code, f"Item {code}"),
                                "done": marker == "1",
                            }
                        )

                    candidates.append(
                        PMOccurrenceCandidate(
                            source_row_number=first,
                            occurrence_date=(row[1] or "").strip() or None if len(row) > 1 else None,
                            tag_number=(row[2] or "").strip() or None if len(row) > 2 else None,
                            source_area=(row[3] or "").strip() or None if len(row) > 3 else None,
                            source_location=(row[4] or "").strip() or None if len(row) > 4 else None,
                            api_plan=(row[5] or "").strip() or None if len(row) > 5 else None,
                            status=(row[6] or "").strip() or None if len(row) > 6 else None,
                            activities=activities,
                            source_page=page_index + 1,
                            raw_row=tuple(row),
                        )
                    )
    return candidates


# ---------------------------------------------------------------------------
# Finding extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    source_row_number: str | None
    source_location: str | None  # e.g. "DCU" -- the Finding table's own area/location column
    tag_number: str | None
    api_plan: str | None
    pump_type: str | None
    seal_leakage_de: bool | None
    seal_leakage_nde: bool | None
    remarks: str | None  # free-text finding, verbatim
    follow_up_date: str | None
    source_page: int | None = None
    raw_row: tuple[str | None, ...] = field(default_factory=tuple)


def extract_finding_candidates(pdf_path: str | Path, page_range: tuple[int, int]) -> list[FindingCandidate]:
    start, end = page_range
    candidates: list[FindingCandidate] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index in range(start - 1, end):
            page = pdf.pages[page_index]
            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0] or not str(row[0]).strip().isdigit():
                        continue
                    candidates.append(
                        FindingCandidate(
                            source_row_number=(row[0] or "").strip() or None,
                            source_location=(row[1] or "").strip() or None if len(row) > 1 else None,
                            tag_number=(row[2] or "").strip() or None if len(row) > 2 else None,
                            api_plan=(row[3] or "").strip() or None if len(row) > 3 else None,
                            pump_type=(row[4] or "").strip() or None if len(row) > 4 else None,
                            seal_leakage_de=_parse_leak_presence(row[5] if len(row) > 5 else None),
                            seal_leakage_nde=_parse_leak_presence(row[6] if len(row) > 6 else None),
                            remarks=_first_nonempty(row[-2:]) if len(row) >= 2 else None,
                            follow_up_date=(row[-1] or "").strip() or None if row and row[-1] else None,
                            source_page=page_index + 1,
                            raw_row=tuple(row),
                        )
                    )
    return candidates


def _parse_leak_presence(raw: str | None) -> bool | None:
    if raw is None:
        return None
    text = raw.strip().upper()
    if text in ("Y", "N"):
        return text == "Y"
    return None


def _first_nonempty(cells: list[str | None]) -> str | None:
    for cell in cells:
        if cell and cell.strip():
            return cell.strip()
    return None


def _clean_workbook_cell(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _normalize_workbook_tag(raw: Any) -> str | None:
    text = _clean_workbook_cell(raw)
    if text is None or text in ("-", "N\\A"):
        return None
    return text


@dataclass(frozen=True, slots=True)
class WorkbookFindingCandidate:
    """XLSX-native equivalent of FindingCandidate above -- added after this
    session's real dry run against all 4 July workbooks proved that
    ltsa_hoc_pm_cm_ingestion.py's own project_finding_rows() is NOT
    compatible with the real "Findings"/"FINDINGS" sheet: that function's
    _FINDING_COLUMNS/_FINDING_DATA_START_ROW were calibrated for a
    different, older 3-column (date/tag/text) workbook, and against the
    real July sheets it silently misreads the API PLAN column as the
    finding text and leaks header rows through as fake data (tag_number=
    "TAG NO."). This function reads the REAL verified layout instead (see
    this module's own header docstring, 'Finding table:' paragraph):
    NO, AREA (sub-unit code e.g. "DCU"/"HVU", NOT the MA business mapping
    -- never conflated with resolve_area()), TAG NO., API PLAN, PUMP TYPE,
    SEAL LEAKAGE DE/NDE, FLUSHING DE/NDE, QUENCHING DE/NDE, REMARKS
    (free-text finding, verbatim), then a trailing column whose own header
    text is a garbled/truncated "N " in every real workbook checked this
    session -- its value is kept verbatim as follow_up_date_raw with no
    asserted meaning (never guessed to be a date just because it looks
    like one), matching this MWO's own never-fabricate rule.

    The header row number itself varies per area (row 8 in HOC's real
    workbook, row 7 in OM_UTL's) so it is located dynamically by scanning
    for the literal "TAG NO." header cell, the same 'derive from the
    actual workbook' approach _pm_checklist_header() already established
    in ltsa_hoc_pm_cm_ingestion.py -- never a hardcoded row number.
    """

    source_sheet_name: str
    source_row_number: int
    source_location: str | None
    tag_number: str
    api_plan: str | None
    pump_type: str | None
    seal_leakage_de: bool | None
    seal_leakage_nde: bool | None
    remarks: str | None
    follow_up_date_raw: str | None


_FINDING_HEADER_TAG_LABEL = "TAG NO."
_FINDING_COLUMN_LOCATION = 2
_FINDING_COLUMN_TAG = 3
_FINDING_COLUMN_API_PLAN = 4
_FINDING_COLUMN_PUMP_TYPE = 5
_FINDING_COLUMN_SEAL_LEAKAGE_DE = 6
_FINDING_COLUMN_SEAL_LEAKAGE_NDE = 7
_FINDING_COLUMN_REMARKS = 12
_FINDING_COLUMN_TRAILING = 13


def _find_finding_header_row(rows: list[tuple[int, dict[int, str | None]]]) -> int | None:
    for row_number, columns in rows:
        for value in columns.values():
            if value is not None and str(value).strip().upper() == _FINDING_HEADER_TAG_LABEL:
                return row_number
    return None


def extract_finding_candidates_from_workbook(
    rows: list[tuple[int, dict[int, str | None]]], *, sheet_name: str
) -> list[WorkbookFindingCandidate]:
    header_row = _find_finding_header_row(rows)
    if header_row is None:
        return []
    data_start_row = header_row + 2  # skips the DE/NDE sub-header row directly beneath

    candidates: list[WorkbookFindingCandidate] = []
    for row_number, columns in rows:
        if row_number < data_start_row:
            continue
        tag_number = _normalize_workbook_tag(columns.get(_FINDING_COLUMN_TAG))
        remarks = _clean_workbook_cell(columns.get(_FINDING_COLUMN_REMARKS))
        if tag_number is None and remarks is None:
            continue  # blank row
        if tag_number is None:
            continue  # cannot ingest a finding with no asset to attach it to

        candidates.append(
            WorkbookFindingCandidate(
                source_sheet_name=sheet_name,
                source_row_number=row_number,
                source_location=_clean_workbook_cell(columns.get(_FINDING_COLUMN_LOCATION)),
                tag_number=tag_number,
                api_plan=_clean_workbook_cell(columns.get(_FINDING_COLUMN_API_PLAN)),
                pump_type=_clean_workbook_cell(columns.get(_FINDING_COLUMN_PUMP_TYPE)),
                seal_leakage_de=_parse_leak_presence(columns.get(_FINDING_COLUMN_SEAL_LEAKAGE_DE)),
                seal_leakage_nde=_parse_leak_presence(columns.get(_FINDING_COLUMN_SEAL_LEAKAGE_NDE)),
                remarks=remarks,
                follow_up_date_raw=_clean_workbook_cell(columns.get(_FINDING_COLUMN_TRAILING)),
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# Document classification (Phase 5)
# ---------------------------------------------------------------------------

DocumentClassification = Literal["PM", "CMON", "MIXED", "UNKNOWN"]


def classify_document(pm_row_count: int, cmon_row_count: int) -> DocumentClassification:
    if pm_row_count > 0 and cmon_row_count > 0:
        return "MIXED"
    if pm_row_count > 0:
        return "PM"
    if cmon_row_count > 0:
        return "CMON"
    return "UNKNOWN"
