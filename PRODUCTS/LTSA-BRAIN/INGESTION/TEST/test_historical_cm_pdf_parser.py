"""LTSA_PDF_CM_PARSER_GENERALIZATION_R1 -- coverage for
historical_cm_pdf_parser.py.

Two layers:

1. Synthetic geometry tests (always run): header/cell geometry is built as
   plain pdfplumber-shaped word/rect dicts, so the layout detection, the
   locked NULL/leak semantics, the body-subdivision guard and the
   report-period quarantine are proven without any customer document.

2. Reference regression (runs only where the real source archive exists,
   e.g. the RYZEN worker; skipped elsewhere): the OM & UTL October 2025
   report must reproduce the POC-verified expected-data contract below.
   The PDF itself is never committed -- only its SHA-256 and the expected
   counts/rows (visually verified against rendered page crops in the POC).
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from historical_cm_pdf_parser import (  # noqa: E402
    CMOccurrence,
    CMRawRow,
    CMRejectedRow,
    LayoutError,
    apply_report_period,
    classify_layout,
    detect_body_subdivisions,
    detect_page_layout,
    extract_raw_rows,
    is_cm_page_text,
    normalize_row,
    normalize_tag,
    parse_cm_pdf,
    parse_source_date,
    validate_rows,
)

# ---------------------------------------------------------------------------
# Synthetic FORMAT_A page geometry
# ---------------------------------------------------------------------------

_CELL = 28.0
_X0 = 200.0  # left edge of the first DE/NDE cell
_GROUPS = [
    ["Flushing", "(°C)"],
    ["Quinch", "(°C)"],
    ["Flushing", "In", "(LBI)"],
    ["Flushing", "Cut", "(LBO)"],
    ["Cooling", "Water", "In"],
    ["Cooling", "Water", "Out"],
    ["Mechseal", "Temp"],
    ["Mechanical", "Seal", "Leak", "(Y/N)"],
    ["Water", "Jacket"],
]
_DE_TOP = 120.0
_ROW_TOP = 140.0


def _w(text: str, x0: float, top: float, width: float | None = None) -> dict:
    width = width if width is not None else max(4.0, 5.0 * len(text))
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 6}


def _vrule(x: float, top: float, bottom: float) -> dict:
    return {"x0": x - 0.25, "x1": x + 0.25, "top": top, "bottom": bottom}


def _cell_centre(index: int) -> float:
    return _X0 + _CELL * index + _CELL / 2


# Left identity columns: (left, right) cell bounds.
_IDENTITY = {"No": (26, 46), "Date": (46, 105), "Tag": (105, 163), "API": (163, 194)}
_SUCTION = (_X0 + 18 * _CELL, _X0 + 18 * _CELL + 50)
_DISCHARGE = (_SUCTION[1], _SUCTION[1] + 50)


def _header_words(*, with_status: bool = False) -> list[dict]:
    words = [
        _w("1", 215, 70),
        _w("Cooler", 350, 70),
        _w("/", 380, 70),
        _w("Thermosyphon", 390, 70),
        _w("API", 170, 76, 14),
        _w("No", 30, 81, 12),
        _w("Date", 66, 81, 18),
        _w("Tag", 110, 81, 14),
        _w("Number", 127, 81, 30),
        _w("PLAN", 167, 87, 22),
    ]
    for g, label in enumerate(_GROUPS):
        left = _X0 + 2 * _CELL * g
        for i, token in enumerate(label):
            words.append(_w(token, left + 4 + i * 10, 90 + (i % 2) * 6, 9))
    words.append(_w("Suction", _SUCTION[0] + 10, 90, 30))
    words.append(_w("Discharge", _DISCHARGE[0] + 5, 90, 40))
    if with_status:
        words.append(_w("Status", _DISCHARGE[1] + 5, 90, 25))
    for i in range(18):
        text = "DE" if i % 2 == 0 else "NDE"
        width = 10 if text == "DE" else 16
        words.append(_w(text, _cell_centre(i) - width / 2, _DE_TOP, width))
    return words


def _rects(*, with_status: bool = False, body_split_cells: tuple[int, ...] = ()) -> list[dict]:
    edges = [26, 46, 105, 163, 194, *[_X0 + _CELL * i for i in range(19)], _SUCTION[1], _DISCHARGE[1]]
    if with_status:
        edges.append(_DISCHARGE[1] + 40)
    rects = [_vrule(x, 60, 400) for x in edges]
    for index in body_split_cells:  # a rule drawn only in the BODY, mid-cell
        rects.append(_vrule(_cell_centre(index), _ROW_TOP - 2, 400))
    return rects


def _row_words(
    number: str, day: str, tag: str, plan: str, cells: dict[int, str], suction: str, discharge: str, top: float
) -> list[dict]:
    words = [
        _w(number, 30, top, 8),
        _w(day, 58, top, 36),
        *[_w(part, 108 + i * 9, top, 7) for i, part in enumerate(tag.split(" "))],
        _w(plan, 168, top, 20),
    ]
    for index, text in cells.items():
        words.append(_w(text, _cell_centre(index) - 4, top, 8))
    words.append(_w(suction, _SUCTION[0] + 20, top, 8))
    words.append(_w(discharge, _DISCHARGE[0] + 20, top, 8))
    return words


def _layout(**kwargs):
    return detect_page_layout(_header_words(**kwargs), _rects(**kwargs), page_number=7)


# ---------------------------------------------------------------------------
# Section detection / layout
# ---------------------------------------------------------------------------


class TestSectionDetection:
    def test_cm_page_needs_title_and_table_headers(self):
        text = "Actual Measuring Report\nNo Date Tag Number PLAN Flushing Mechseal\nDE NDE DE NDE"
        assert is_cm_page_text(text)

    def test_pm_and_summary_pages_are_not_cm_pages(self):
        assert not is_cm_page_text("PROGRESS SUMMARY CM\nTARGET ACHIEVEMENT CONDITION MONITORING")
        assert not is_cm_page_text("CONDITION MONITORING ACTUAL MEASURING REPORT\nLTSA PREVENTIVE MAINTENANCE")


class TestLayoutDetection:
    def test_format_a_columns_are_identified_from_header_words(self):
        layout = _layout()
        keys = [c.raw_key for c in layout.columns]
        assert keys[:4] == ["source_row_number", "raw_date", "raw_tag", "raw_api_plan"]
        assert keys[4:6] == ["flushing_temp_de", "flushing_temp_nde"]
        assert keys[6:8] == ["quench_temp_de", "quench_temp_nde"]
        assert keys[8:10] == ["flushing_in_temp_de", "flushing_in_temp_nde"]
        assert keys[10:12] == ["flushing_out_temp_de", "flushing_out_temp_nde"]
        assert keys[18:20] == ["mechanical_seal_leak_de", "mechanical_seal_leak_nde"]
        assert keys[-2:] == ["suction_temp", "discharge_temp"]
        assert layout.boundary_method == "TABLE_RECTS"
        assert classify_layout(layout) == "FORMAT_A_COMPATIBLE"

    def test_source_labels_are_preserved_verbatim(self):
        labels = {c.raw_key: c.source_label for c in _layout().columns}
        assert labels["quench_temp_de"].startswith("Quinch")
        assert "Cut" in labels["flushing_out_temp_nde"] and "(LBO)" in labels["flushing_out_temp_nde"]

    def test_trailing_status_column_is_a_configurable_variant(self):
        layout = _layout(with_status=True)
        assert layout.columns[-1].raw_key == "pump_operating_state"
        assert classify_layout(layout) == "CONFIGURABLE_VARIANT"

    def test_fragmented_api_plan_header_is_accepted_only_as_exact_letters(self):
        words = [w for w in _header_words() if w["text"] not in ("API", "PLAN")]
        words += [_w("P", 168, 86, 4), _w("A", 171, 80, 4), _w("LA", 172, 86, 8), _w("PI", 176, 80, 6), _w("N", 181, 86, 4)]
        layout = detect_page_layout(words, _rects(), page_number=1)
        assert "FRAGMENTED_HEADER_LABELS" in layout.variant_notes
        assert classify_layout(layout) == "CONFIGURABLE_VARIANT"

    def test_unrecognised_group_header_raises_instead_of_guessing(self):
        words = [w for w in _header_words() if w["text"] != "Mechseal"]
        words.append(_w("Bearing", _X0 + 12 * _CELL + 4, 90, 9))
        with pytest.raises(LayoutError):
            detect_page_layout(words, _rects(), page_number=1)

    def test_missing_de_nde_row_raises(self):
        words = [w for w in _header_words() if w["text"] not in ("DE", "NDE")]
        with pytest.raises(LayoutError):
            detect_page_layout(words, _rects(), page_number=1)

    def test_falls_back_to_header_midpoints_without_table_rules(self):
        layout = detect_page_layout(_header_words(), [], page_number=1)
        assert layout.boundary_method == "HEADER_MIDPOINTS"
        assert [c.raw_key for c in layout.columns] == [c.raw_key for c in _layout().columns]


# ---------------------------------------------------------------------------
# Raw extraction + canonical semantics
# ---------------------------------------------------------------------------


def _extract(row_specs: list[list[dict]], **layout_kwargs):
    layout = _layout(**layout_kwargs)
    words = _header_words(**layout_kwargs) + [w for row in row_specs for w in row]
    return extract_raw_rows(words, layout, source_document="synthetic.pdf", source_hash="0" * 64)


class TestSemantics:
    def test_sparse_row_keeps_blanks_as_none(self):
        rows, _ = _extract([_row_words("19", "06-Oct-25", "110-P-1B", "11/62", {0: "57", 2: "50", 12: "55", 14: "N"}, "57", "58", _ROW_TOP)])
        occurrence = normalize_row(rows[0])
        assert isinstance(occurrence, CMOccurrence)
        m = occurrence.measurements
        assert m["flushing_temp_de"] == 57 and m["flushing_temp_nde"] is None
        assert m["quench_temp_de"] == 50 and m["quench_temp_nde"] is None
        assert m["mechseal_temp_de"] == 55 and m["mechseal_temp_nde"] is None  # never DE -> NDE
        assert m["mechanical_seal_leak_de"] is False and m["mechanical_seal_leak_nde"] is None
        assert m["water_jacket_temp_de"] is None
        assert (m["suction_temp"], m["discharge_temp"]) == (57, 58)

    def test_leak_tristate(self):
        rows, _ = _extract(
            [
                _row_words("1", "01-Oct-25", "940-P-1B", "11/61", {0: "35", 12: "36", 14: "Y"}, "36", "35", _ROW_TOP),
                _row_words("2", "01-Oct-25", "940-P-2A", "23/61", {0: "59", 12: "65", 14: "N", 15: "N"}, "120", "115", _ROW_TOP + 15),
                _row_words("3", "01-Oct-25", "920-P-1B", "11/62", {0: "66", 12: "65"}, "77", "76", _ROW_TOP + 30),
            ]
        )
        leaks = [
            (o.measurements["mechanical_seal_leak_de"], o.measurements["mechanical_seal_leak_nde"])
            for o in map(normalize_row, rows)
        ]
        assert leaks == [(True, None), (False, False), (None, None)]

    def test_rows_are_never_forward_filled_from_previous_row(self):
        rows, _ = _extract(
            [
                _row_words("1", "01-Oct-25", "940-P-2A", "23/61", {0: "59", 1: "59", 12: "65", 13: "68"}, "120", "115", _ROW_TOP),
                _row_words("2", "01-Oct-25", "940-P-3C", "11/61", {12: "90"}, "110", "115", _ROW_TOP + 15),
            ]
        )
        second = normalize_row(rows[1])
        assert second.measurements["flushing_temp_de"] is None
        assert second.measurements["mechseal_temp_nde"] is None

    def test_api_plan_is_a_row_snapshot(self):
        rows, _ = _extract([_row_words("4", "01-Oct-25", "940-P-2A", "23/61", {12: "65"}, "120", "115", _ROW_TOP)])
        occurrence = normalize_row(rows[0])
        assert occurrence.api_plan_snapshot == "23/61"
        assert rows[0].raw_api_plan == "23/61"

    def test_spaced_tag_is_preserved_raw_and_collapsed_canonically(self):
        rows, _ = _extract([_row_words("1", "9-Jan-26", "200 - P - 1A", "11/61", {12: "42"}, "45", "44", _ROW_TOP)])
        assert rows[0].raw_tag == "200 - P - 1A"
        occurrence = normalize_row(rows[0])
        assert occurrence.asset_code == "200-P-1A"
        assert occurrence.reading_date == "2026-01-09"

    def test_invalid_leak_and_non_numeric_values_reject_the_row(self):
        rows, _ = _extract([_row_words("5", "01-Oct-25", "940-P-5A", "11/61", {12: "5x", 14: "maybe"}, "53", "54", _ROW_TOP)])
        result = normalize_row(rows[0])
        assert isinstance(result, CMRejectedRow)
        assert any("non-numeric" in r for r in result.reasons)
        assert any("invalid leak" in r for r in result.reasons)

    def test_unparseable_date_rejects_the_row(self):
        rows, _ = _extract([_row_words("6", "32-Oct-25", "940-P-5A", "11/61", {12: "50"}, "53", "54", _ROW_TOP)])
        assert isinstance(normalize_row(rows[0]), CMRejectedRow)

    def test_marker_line_without_row_identity_is_non_data(self):
        layout = _layout()
        words = _header_words() + [_w("TA", 400, _ROW_TOP + 50, 30)]
        rows, non_data = extract_raw_rows(words, layout, source_document="s.pdf", source_hash="0" * 64)
        assert rows == []
        assert [n["text"] for n in non_data] == ["TA"]

    def test_status_column_maps_to_pump_operating_state(self):
        row = _row_words("1", "9-Jan-26", "200-P-1A", "11/61", {12: "42"}, "45", "44", _ROW_TOP)
        row.append(_w("Running", _DISCHARGE[1] + 8, _ROW_TOP, 28))
        rows, _ = _extract([row], with_status=True)
        assert normalize_row(rows[0]).measurements["pump_operating_state"] == "Running"


class TestStructureGuards:
    def test_body_subdivision_under_a_de_cell_is_detected(self):
        layout = _layout()
        split = detect_body_subdivisions(_rects(body_split_cells=(4, 5)), layout, _ROW_TOP - 5, 400)
        assert split == ["flushing_in_temp_de", "flushing_in_temp_nde"]

    def test_format_a_body_has_no_subdivision(self):
        assert detect_body_subdivisions(_rects(), _layout(), _ROW_TOP - 5, 400) == []

    def test_date_outside_report_period_is_quarantined_not_corrected(self):
        rows, _ = _extract([_row_words("1", "06-Jan-25", "140-P-3A", "11/61", {12: "40"}, "41", "42", _ROW_TOP)])
        occurrence = normalize_row(rows[0])
        apply_report_period([occurrence], (2026, 1))
        assert occurrence.reading_date == "2025-01-06"
        assert occurrence.quarantine_reasons

    def test_validation_reports_gaps_and_duplicates(self):
        specs = [
            _row_words(str(n), "01-Oct-25", "940-P-1B", "11/61", {12: "35"}, "36", "35", _ROW_TOP + 15 * i)
            for i, n in enumerate([1, 2, 2, 5])
        ]
        rows, _ = _extract(specs)
        results = [normalize_row(r) for r in rows]
        report = validate_rows(rows, [r for r in results if isinstance(r, CMOccurrence)], [], [_layout()])
        assert report["missing_source_row_numbers"] == [3, 4]
        assert report["duplicate_source_row_numbers"] == [2]


class TestHelpers:
    def test_date_formats(self):
        assert parse_source_date("01-Oct-25").isoformat() == "2025-10-01"
        assert parse_source_date("9-Jan-26").isoformat() == "2026-01-09"
        assert parse_source_date("31-Feb-26") is None
        assert parse_source_date(None) is None

    def test_normalize_tag_is_typography_only(self):
        assert normalize_tag(" dmi-p-201a ") == "DMI-P-201A"
        assert normalize_tag("100 - P - 6B") == "100-P-6B"
        assert normalize_tag("  ") is None


# ---------------------------------------------------------------------------
# Reference regression -- OM & UTL October 2025 (real source PDF)
# ---------------------------------------------------------------------------

_ARCHIVE_ROOT = Path(os.environ.get("LTSA_PM_CM_HISTORY_ROOT", r"D:\PROJECT\Source-documents\LTSA\PM_CM_HISTORY"))
_REFERENCE_PDF = _ARCHIVE_ROOT / "2025" / "OM_UTL" / "Laporan PM, CM & Pemasangan Seal OM & UTL OKTOBER 25.pdf"
_REFERENCE_SHA256 = "981221136e52253ba58995628bf40603eab2417fc049c2031dc4b061de45e3bf"

# (page, row) -> (date, tag, api_plan, flushing DE/NDE, mechseal DE/NDE, leak DE/NDE, suction, discharge)
# Visually verified against rendered source crops (rows 16/29 via text layer + cell-rect cross-check).
_SPOT_ROWS = {
    19: (41, "06-Oct-25", "110-P-1B", "11/62", (57, None), (55, None), (False, None), 57, 58),
    7: (40, "02-Oct-25", "200-P-7A", "11/61", (42, 43), (41, 45), (False, False), 44, 47),
    4: (40, "01-Oct-25", "940-P-2A", "23/61", (59, 59), (65, 68), (False, False), 120, 115),
    2: (40, "01-Oct-25", "940-P-1B", "11/61", (35, None), (36, None), (True, None), 36, 35),
    81: (43, "23-Oct-25", "945-P-7C", "11/53", (40, None), (54, None), (False, None), 33, 35),
    23: (41, "07-Oct-25", "DMI-P-201A", "02", (None, None), (48, None), (False, None), 48, 47),
    24: (41, "07-Oct-25", "DMI-P-201B", "02", (None, None), (40, None), (False, None), 48, 47),
    16: (40, "03-Oct-25", "940-P-2A", "23/61", (52, 51), (60, 63), (False, False), 120, 110),
    29: (41, "08-Oct-25", "940-P-2A", "23/61", (61, 58), (62, 67), (False, False), 120, 117),
    36: (41, "09-Oct-25", "920-P-1B", "11/62", (66, None), (65, None), (None, None), 77, 76),
}


@pytest.fixture(scope="module")
def reference_result():
    if not _REFERENCE_PDF.exists():
        pytest.skip(f"reference source PDF not present on this machine: {_REFERENCE_PDF}")
    return parse_cm_pdf(_REFERENCE_PDF, report_period=(2025, 10))


class TestOmUtlOctober2025Regression:
    def test_source_identity(self, reference_result):
        assert reference_result.source_hash == _REFERENCE_SHA256
        assert reference_result.page_count == 58
        assert reference_result.cm_pages == [40, 41, 42, 43, 44, 45]
        assert reference_result.format_class == "FORMAT_A_COMPATIBLE"

    def test_row_counts_and_continuity(self, reference_result):
        v = reference_result.validation
        assert len(reference_result.raw_rows) == 123
        assert len(reference_result.occurrences) == 123
        assert len(reference_result.rejected) == 0
        assert [o.source_row_number for o in reference_result.occurrences] == list(range(1, 124))
        assert v["missing_source_row_numbers"] == [] and v["duplicate_source_row_numbers"] == []
        assert v["quarantined_rows"] == 0
        assert (v["date_min"], v["date_max"]) == ("2025-10-01", "2025-10-31")

    def test_api_plan_distribution(self, reference_result):
        assert Counter(o.api_plan_snapshot for o in reference_result.occurrences) == {
            "11/61": 84,
            "11/62": 22,
            "23/61": 10,
            "02": 6,
            "11/53": 1,
        }

    def test_leak_distribution(self, reference_result):
        occ = reference_result.occurrences
        assert Counter(o.measurements["mechanical_seal_leak_de"] for o in occ) == {False: 107, True: 11, None: 5}
        assert Counter(o.measurements["mechanical_seal_leak_nde"] for o in occ) == {False: 27, None: 96}

    @pytest.mark.parametrize("row_number", sorted(_SPOT_ROWS))
    def test_spot_rows(self, reference_result, row_number):
        page, day, tag, plan, flushing, mechseal, leak, suction, discharge = _SPOT_ROWS[row_number]
        o = next(o for o in reference_result.occurrences if o.source_row_number == row_number)
        m = o.measurements
        assert (o.source_page, o.source_date, o.source_tag, o.api_plan_snapshot) == (page, day, tag, plan)
        assert (m["flushing_temp_de"], m["flushing_temp_nde"]) == flushing
        assert (m["mechseal_temp_de"], m["mechseal_temp_nde"]) == mechseal
        assert (m["mechanical_seal_leak_de"], m["mechanical_seal_leak_nde"]) == leak
        assert (m["suction_temp"], m["discharge_temp"]) == (suction, discharge)

    def test_raw_layer_is_preserved(self, reference_result):
        raw = next(r for r in reference_result.raw_rows if r.source_row_number == "4")
        assert isinstance(raw, CMRawRow)
        assert raw.source_hash == _REFERENCE_SHA256
        assert raw.raw_values["flushing_in_temp_de"] == "76"
        assert raw.source_labels["quench_temp_de"].startswith("Quinch")


# ---------------------------------------------------------------------------
# Archive dry-run metadata (historical_cm_pdf_archive_dry_run.py)
# ---------------------------------------------------------------------------

from historical_cm_pdf_archive_dry_run import derive_metadata, document_is_eligible  # noqa: E402


class TestArchiveMetadata:
    ROOT = Path("/archive")

    def _meta(self, relative: str) -> dict:
        return derive_metadata(self.ROOT / relative, self.ROOT)

    @pytest.mark.parametrize(
        ("relative", "month", "area"),
        [
            ("2025/OM_UTL/Laporan PM, CM & Pemasangan Seal OM & UTL OKTOBER 25.pdf", 10, "OM_UTL"),
            ("2026/2. FEBUARI/HSC/Laporan PM, CM & Pemasangan Seal HSC & SPK FEBUARI '26.pdf", 2, "HSC_SPK"),
            ("2026/5. MEI/HOC/Laporan PM, CM & Pemasangan Seal HOC MAY 2026.pdf", 5, "HOC"),
            ("2026/6. JUNI/OM UTL/Laporan PM, CM & Pemasangan Seal OM & UTL june '26.pdf", 6, "OM_UTL"),
        ],
    )
    def test_year_month_area_from_path(self, relative, month, area):
        meta = self._meta(relative)
        assert (meta["year"], meta["month"], meta["area"]) == (int(relative[:4]), month, area)
        assert meta["metadata_warnings"] == []

    def test_folder_and_file_name_area_mismatch_is_a_warning(self):
        meta = self._meta("2025/HOC/Laporan PM, CM & Pemasangan Seal HCC DECEMBER 2025.pdf")
        assert meta["area"] == "HCC" and meta["folder_area"] == "HOC"
        assert meta["metadata_warnings"]
        record = {**meta, "discovery_status": "CM_SECTION_FOUND", "format_class": "FORMAT_A_COMPATIBLE"}
        assert document_is_eligible(record) is False

    def test_new_adapter_documents_are_never_eligible(self):
        meta = self._meta("2026/1. JANUARY/HSC SPK/Laporan PM, CM & Pemasangan Seal HSC & SPK JAN '26.pdf")
        record = {**meta, "discovery_status": "CM_SECTION_FOUND", "format_class": "NEW_ADAPTER_REQUIRED"}
        assert document_is_eligible(record) is False
