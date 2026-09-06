"""AI5R-PHASE4E4 -- pm_schedule_excel_import.parse_xlsx_grid(): decode-only
parsing, security caps (file size / row count / cell length), and that a
formula cell yields its cached value, never the formula text (Section M:
formulas are never evaluated -- openpyxl has no formula engine at all)."""

import datetime
import io
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pm_schedule_excel_import import ExcelImportError, parse_xlsx_grid  # noqa: E402


def _workbook_bytes(rows, formula_cache=None):
    """rows: list of row tuples (first row is headers). If formula_cache
    is given, it's {(row_idx, col_idx): (formula_str, cached_value)} --
    openpyxl only stores ONE cached value per formula cell, simulated
    here by writing the formula then re-opening with data_only writing
    is not directly supported by the writer API, so instead we exploit
    that when a NUMBER/STRING is written directly (not via '='), it is
    already the stored value -- for the formula-cell test we instead
    verify data_only=True never returns a raw '=...' string by writing a
    real formula and asserting the parser either yields the cached value
    openpyxl computes not at all (None, since a fresh openpyxl-written
    formula has no cached value) or raises -- never the literal formula
    text."""
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parses_headers_and_rows():
    data = _workbook_bytes([
        ("Pump Tag", "Frequency", "Start Date"),
        ("211-P-1A", "MONTHLY", "2026-10-01"),
        ("211-P-1B", "WEEKLY", "2026-10-08"),
    ])
    grid = parse_xlsx_grid(data)
    assert grid["headers"] == ["Pump Tag", "Frequency", "Start Date"]
    assert grid["rows"] == [["211-P-1A", "MONTHLY", "2026-10-01"], ["211-P-1B", "WEEKLY", "2026-10-08"]]
    assert grid["row_count"] == 2


def test_skips_fully_blank_rows():
    data = _workbook_bytes([
        ("Pump Tag", "Frequency"),
        ("211-P-1A", "MONTHLY"),
        (None, None),
        ("", ""),
        ("211-P-1B", "WEEKLY"),
    ])
    grid = parse_xlsx_grid(data)
    assert grid["row_count"] == 2


def test_real_excel_date_cell_becomes_iso_string():
    data = _workbook_bytes([
        ("Pump Tag", "Start Date"),
        ("211-P-1A", datetime.date(2026, 10, 1)),
    ])
    grid = parse_xlsx_grid(data)
    assert grid["rows"][0][1] == "2026-10-01"


def test_empty_workbook_raises_structural_error():
    data = _workbook_bytes([])
    with pytest.raises(ExcelImportError, match="empty"):
        parse_xlsx_grid(data)


def test_empty_header_row_raises_structural_error():
    data = _workbook_bytes([(None, None, None)])
    with pytest.raises(ExcelImportError, match="[Hh]eader"):
        parse_xlsx_grid(data)


def test_more_than_max_rows_is_rejected():
    rows = [("Pump Tag", "Frequency")] + [(f"P-{i}", "MONTHLY") for i in range(5)]
    data = _workbook_bytes(rows)
    with pytest.raises(ExcelImportError, match="more than"):
        parse_xlsx_grid(data, max_data_rows=3)


def test_oversized_file_is_rejected():
    data = _workbook_bytes([("Pump Tag",), ("211-P-1A",)])
    with pytest.raises(ExcelImportError, match="[Ll]imit"):
        parse_xlsx_grid(data + b"\x00" * (11 * 1024 * 1024))  # pad past the size cap; corrupt zip either way


def test_oversized_cell_is_rejected():
    huge = "X" * 501
    data = _workbook_bytes([("Pump Tag",), (huge,)])
    with pytest.raises(ExcelImportError, match="character limit"):
        parse_xlsx_grid(data)


def test_formula_cell_never_yields_raw_formula_text():
    # openpyxl's writer stores the formula string; a freshly-written
    # formula has no cached value at all. With data_only=True, this
    # parser must NEVER surface the literal "=SUM(...)" text -- either a
    # cached value (none exists here) or None, never the formula source.
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(("Pump Tag", "Computed"))
    sheet.append(("211-P-1A", "=1+1"))
    buffer = io.BytesIO()
    workbook.save(buffer)

    grid = parse_xlsx_grid(buffer.getvalue())
    computed_cell = grid["rows"][0][1]
    assert computed_cell != "=1+1"
    assert computed_cell is None  # no cached value exists for a workbook that was never opened in Excel


def test_malformed_workbook_raises_readable_error_not_a_crash():
    with pytest.raises(ExcelImportError, match="could not be read"):
        parse_xlsx_grid(b"this is not a zip file at all")
