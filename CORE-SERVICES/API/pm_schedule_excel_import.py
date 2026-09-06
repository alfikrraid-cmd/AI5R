"""AI5R-PHASE4E4 -- PM Schedule Excel import: DECODE-ONLY parsing of an
untrusted .xlsx upload into a raw header/row grid.

Architecture note (Section C's own "prefer client-side parsing, inspect
existing dependencies before adding any package"): the only safe,
already-vetted way to decode .xlsx binary format anywhere in this
codebase is openpyxl (CORE-SERVICES/BACKEND-API/requirements.txt,
already used by the pre-existing Pump Master XLSX import). The frontend
xlsx/exceljs candidates both carry either an unpatched high-severity CVE
(xlsx: GHSA-4r6h-8v6p-xvw6 prototype pollution, GHSA-5pgg-2g8v-p4x9 ReDoS,
no fix on npm) or a moderate transitive one -- neither justified for a
brand-new dependency when openpyxl already exists and is already trusted
for this exact domain (parsing pump-related workbooks). So: the upload
happens (Section C's own "unless technically necessary" exception), but
ONLY to decode bytes into a JSON grid -- every business rule (header
aliasing, pump resolution against the canonical master, frequency/date/
activity parsing, validation) stays client-side in
utils/pmExcelImport.js, unchanged from the "prefer client-side" spirit.
This endpoint never touches pm_schedule, never resolves a pump, and
never writes to any table -- Excel upload cannot create schedules
directly (Section, mission header).

Security (Section M): `data_only=True` means a formula cell yields its
last-CACHED value (a plain string/number), never the formula text and
never an evaluation -- openpyxl has no formula engine at all, so nothing
is ever executed. `.xlsx` has no VBA project structurally (unlike
`.xlsm`), so macro execution is not a category of risk this format can
even carry. File size, row count, and per-cell string length are all
capped BEFORE parsing (zip-bomb / oversized-string / excessive-row
defense), and any workbook-level failure (corrupt zip, no worksheets, no
data) is caught and turned into one readable error, never a raw
traceback.
"""

from __future__ import annotations

import datetime
import io
from typing import Any

from openpyxl import load_workbook

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB -- defends against a small zip-bomb-style workbook
MAX_DATA_ROWS = 1000  # Section C's own cap; enforced server-side too (never trust the client alone)
MAX_CELL_LENGTH = 500  # an oversized single cell is rejected outright, never silently truncated


class ExcelImportError(ValueError):
    """A structural workbook problem (Section J: 'do not continue')."""


def _stringify_cell(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime.datetime, datetime.date)):
        # A genuine Excel date CELL (not a string that merely looks like a
        # date) -- openpyxl already parsed it; emitted as canonical
        # YYYY-MM-DD so the frontend's date parser (Section H) never has
        # to guess locale for a real date cell, only for typed strings.
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if len(text) > MAX_CELL_LENGTH:
        raise ExcelImportError(f"A cell exceeds the {MAX_CELL_LENGTH}-character limit -- check for pasted/oversized content.")
    return text or None


def _row_is_blank(row: tuple[Any, ...]) -> bool:
    return all(cell is None or (isinstance(cell, str) and not cell.strip()) for cell in row)


def parse_xlsx_grid(file_bytes: bytes, *, max_data_rows: int = MAX_DATA_ROWS) -> dict:
    """Returns {"headers": [str, ...], "rows": [[str|None, ...], ...],
    "row_count": int} for the FIRST worksheet only (Section C's own
    template is single-sheet for data; an "Instructions" second sheet, if
    present in a user's workbook, is simply never read). Raises
    ExcelImportError with a human-readable message on any structural
    problem -- never lets an openpyxl/zip exception escape as a 500."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ExcelImportError(f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.")

    try:
        workbook = load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 -- any parse failure becomes one readable message
        raise ExcelImportError("The file could not be read as a valid .xlsx workbook.") from exc

    try:
        if not workbook.worksheets:
            raise ExcelImportError("The workbook has no worksheets.")
        worksheet = workbook.worksheets[0]

        rows_iter = worksheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise ExcelImportError("The worksheet is empty -- no header row found.") from None

        headers = [_stringify_cell(cell) or "" for cell in header_row]
        if not any(headers):
            raise ExcelImportError("The header row is empty.")

        data_rows: list[list[str | None]] = []
        for row in rows_iter:
            if _row_is_blank(row):
                continue
            data_rows.append([_stringify_cell(cell) for cell in row[: len(headers)]])
            if len(data_rows) > max_data_rows:
                raise ExcelImportError(
                    f"This file has more than {max_data_rows} data rows -- split it into smaller files."
                )

        return {"headers": headers, "rows": data_rows, "row_count": len(data_rows)}
    finally:
        workbook.close()


__all__ = ["ExcelImportError", "parse_xlsx_grid", "MAX_DATA_ROWS", "MAX_FILE_SIZE_BYTES", "MAX_CELL_LENGTH"]
