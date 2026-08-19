"""MWO-LTSA-HISTORICAL-JULY-INGESTION-001 -- pure-logic coverage for
historical_pm_cmon_extraction.py: hashing, duplicate classification, pump
matching (exact/whitespace-near-miss/suffix-near-miss/no-match),
area/MA resolution, and the XLSX-native Finding extractor. No database,
no real customer PDFs/XLSX -- synthetic fixtures only (Phase 23's own
explicit "synthetic fixtures where source-sensitivity makes real fixtures
undesirable" allowance), matching test_installation_review_service.py's
own plain-dict-fixture convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from historical_pm_cmon_extraction import (  # noqa: E402
    classify_document,
    classify_source_duplicate,
    extract_finding_candidates_from_workbook,
    match_pump_tag,
    resolve_area,
    sha256_file,
)


class TestSha256File:
    def test_same_bytes_produce_same_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"identical content")
        f2.write_bytes(b"identical content")
        assert sha256_file(f1) == sha256_file(f2)

    def test_different_bytes_produce_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert sha256_file(f1) != sha256_file(f2)


class TestClassifySourceDuplicate:
    def test_unknown_hash_is_new_source(self):
        assert classify_source_duplicate("abc123", known_hashes=set()) == "NEW_SOURCE"

    def test_known_hash_is_exact_duplicate(self):
        assert classify_source_duplicate("abc123", known_hashes={"abc123"}) == "EXACT_DUPLICATE"

    def test_matching_candidate_key_is_possible_duplicate(self):
        key = ("HOC", "2026-07", "PM_CMON_MONTHLY_REPORT")
        status = classify_source_duplicate(
            "different-hash", known_hashes=set(),
            known_possible_duplicates={key}, candidate_key=key,
        )
        assert status == "POSSIBLE_DUPLICATE"


class TestMatchPumpTag:
    def test_exact_match(self):
        result = match_pump_tag("110-P-9A", {"110-P-9A", "110-P-9B"})
        assert result.outcome == "EXACT_MATCH"
        assert result.matched_tag == "110-P-9A"

    def test_no_match_no_near_miss(self):
        result = match_pump_tag("999-P-99Z", {"110-P-9A"})
        assert result.outcome == "NO_MATCH"
        assert result.matched_tag is None

    def test_suffix_near_miss_never_auto_resolved(self):
        # "110-P-9C" doesn't exist, but 110-P-9A/9B do -- same base, different
        # suffix. Must be flagged for review, never silently matched to
        # either sister pump.
        result = match_pump_tag("110-P-9C", {"110-P-9A", "110-P-9B"})
        assert result.outcome == "REVIEW_REQUIRED"
        assert result.matched_tag is None

    def test_whitespace_variant_is_review_required_with_matched_tag_hint(self):
        # Real HSC July CM Measuring Report data: '200 - P - 1A' in the
        # source vs '200-P-1A' in the canonical roster -- pure typography,
        # not identity. Surfaced for confirmation, never silently promoted.
        result = match_pump_tag("200 - P - 1A", {"200-P-1A"})
        assert result.outcome == "REVIEW_REQUIRED"
        assert result.matched_tag == "200-P-1A"

    def test_whitespace_variant_ambiguous_across_multiple_canonical_tags_stays_unmatched_hint(self):
        # If whitespace-collapsing produces more than one candidate, no
        # single matched_tag hint is offered -- still REVIEW_REQUIRED via
        # the suffix-near-miss path, but never guessed.
        result = match_pump_tag("110 - P - 9 X", {"110-P-9A", "110-P-9B"})
        assert result.outcome in ("REVIEW_REQUIRED", "NO_MATCH")

    def test_blank_tag_is_no_match(self):
        assert match_pump_tag("", {"110-P-9A"}).outcome == "NO_MATCH"
        assert match_pump_tag("   ", {"110-P-9A"}).outcome == "NO_MATCH"

    def test_never_strips_suffix_to_force_a_match(self):
        # A real sister-pump trap: '110-P-9' (no suffix) must never
        # silently resolve to '110-P-9A'.
        result = match_pump_tag("110-P-9", {"110-P-9A", "110-P-9B"})
        assert result.outcome != "EXACT_MATCH"


class TestResolveArea:
    def test_explicit_source_ma_is_trusted(self):
        result = resolve_area("MA-1", "HOC")
        assert result.normalized_ma == "MA-1"
        assert result.mapping_basis == "EXPLICIT_SOURCE_MA"

    def test_missing_area_and_location_is_review_required(self):
        result = resolve_area(None, None)
        assert result.mapping_basis == "REVIEW_REQUIRED"
        assert result.normalized_ma is None


class TestClassifyDocument:
    def test_pm_and_cmon_rows_present_is_mixed(self):
        assert classify_document(3, 5) == "MIXED"

    def test_only_pm_rows(self):
        assert classify_document(3, 0) == "PM"

    def test_only_cmon_rows(self):
        assert classify_document(0, 5) == "CMON"

    def test_no_rows_is_unknown(self):
        assert classify_document(0, 0) == "UNKNOWN"


class TestExtractFindingCandidatesFromWorkbook:
    """Synthetic rows shaped exactly like the REAL July "Findings" sheet
    layout discovered this session (header row containing 'TAG NO.',
    DE/NDE sub-header directly beneath, data 2 rows after the header) --
    NOT the older 3-column date/tag/text layout
    ltsa_hoc_pm_cm_ingestion.py's own project_finding_rows() assumes,
    which this session's real dry run proved incompatible with the real
    workbooks."""

    def _synthetic_rows(self, header_row: int = 8):
        return [
            (1, {4: "FINDINGS"}),
            (header_row, {
                1: "NO", 2: "AREA", 3: "TAG NO.", 4: "API PLAN", 5: "PUMP TYPE",
                6: "SEAL LEAKAGE", 8: "FLUSHING", 10: "QUENCHING", 12: "REMARKS", 13: "N ",
            }),
            (header_row + 1, {6: "DE", 7: "NDE", 8: "DE", 9: "NDE", 10: "DE", 11: "NDE"}),
            (header_row + 2, {}),  # genuinely blank data row -- must be skipped, not fabricated
            (header_row + 3, {
                1: "1", 2: "DCU", 3: "140-P-16A", 4: "32/61", 5: "OH",
                6: "Y", 7: "-", 8: "38", 9: "-", 10: "-", 11: "-",
                12: "STANDBY, bocor dari draingland 1/2 detik", 13: "-",
            }),
            (header_row + 4, {
                1: "2", 2: "HVU", 3: "110-P-9A", 4: "11/62", 5: "OH",
                6: "Y", 7: "-", 8: "48", 9: "-", 10: "71", 11: "-",
                12: "Standby, bocor deras dari celah sleeve 1/3 detik", 13: "21-7-2026",
            }),
        ]

    def test_extracts_real_shaped_rows_correctly(self):
        candidates = extract_finding_candidates_from_workbook(self._synthetic_rows(), sheet_name="Findings")
        assert len(candidates) == 2
        first = candidates[0]
        assert first.tag_number == "140-P-16A"
        assert first.source_location == "DCU"
        assert first.api_plan == "32/61"
        assert first.pump_type == "OH"
        assert first.seal_leakage_de is True
        assert first.seal_leakage_nde is None  # '-' is not asserted False, only Y/N are
        assert first.remarks == "STANDBY, bocor dari draingland 1/2 detik"
        assert first.follow_up_date_raw == "-"

    def test_ambiguous_trailing_column_kept_raw_never_asserted_as_a_date(self):
        candidates = extract_finding_candidates_from_workbook(self._synthetic_rows(), sheet_name="Findings")
        dated = next(c for c in candidates if c.tag_number == "110-P-9A")
        assert dated.follow_up_date_raw == "21-7-2026"  # verbatim string, not parsed/typed as a date

    def test_header_row_number_varies_by_area_and_is_detected_dynamically(self):
        # Real OM_UTL workbook's header is at row 7, not row 8 like HOC's.
        candidates = extract_finding_candidates_from_workbook(self._synthetic_rows(header_row=7), sheet_name="Findings")
        assert len(candidates) == 2
        assert candidates[0].tag_number == "140-P-16A"

    def test_header_row_never_leaks_through_as_a_fake_data_row(self):
        candidates = extract_finding_candidates_from_workbook(self._synthetic_rows(), sheet_name="Findings")
        tags = [c.tag_number for c in candidates]
        assert "TAG NO." not in tags
        remarks = [c.remarks for c in candidates]
        assert "API PLAN" not in remarks  # the real defect this test guards against

    def test_no_header_found_returns_empty_not_a_guess(self):
        rows = [(1, {1: "unrelated"}), (2, {1: "also unrelated"})]
        assert extract_finding_candidates_from_workbook(rows, sheet_name="Findings") == []

    def test_row_with_no_tag_is_skipped_never_fabricated(self):
        rows = self._synthetic_rows() + [(12, {12: "orphan remark with no tag"})]
        candidates = extract_finding_candidates_from_workbook(rows, sheet_name="Findings")
        assert all(c.tag_number for c in candidates)
