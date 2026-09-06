"""AI5R-PHASE4E4, Section D/O -- generates the downloadable PM Schedule
Excel import template: a static workbook with no user-controllable
content, so the formula-injection escaping this module exposes
(escape_formula_leading, Section M) is exercised defensively here even
though nothing on the fixed template sheet is attacker-influenced -- it
exists as the one shared helper any FUTURE export of parsed/echoed
values (e.g. an "download rows with errors" feature) must also route
through, so that discipline is established from the first caller.
"""

from __future__ import annotations

import io

from openpyxl import Workbook

# Section D -- exactly these columns, in this order. NO Schedule Code, NO
# Status, NO Trigger Type, NO Procedure, NO Checklist Template, NO audit
# fields (all system-managed/derived, never user-supplied -- OWNER
# DECISIONS 1-5, Section B of 4E.2).
TEMPLATE_COLUMNS = (
    "Pump Tag *",
    "Frequency *",
    "Start Date *",
    "Planned Activities",
    "Assigned Technician",
    "Estimated Duration",
    "Notes",
)

_FORMULA_LEADING_CHARS = ("=", "+", "-", "@")


def escape_formula_leading(value: str) -> str:
    """Section M -- a string beginning with =, +, -, or @ is interpreted
    as a formula by Excel/LibreOffice/Sheets when the cell is later
    opened; prefixing with a literal apostrophe forces text
    interpretation. Applied to any value written into a workbook this
    codebase generates that did not originate as a fixed literal here."""
    if value and value[0] in _FORMULA_LEADING_CHARS:
        return "'" + value
    return value


_INSTRUCTIONS = (
    ("PM Schedule Import -- Instructions", None),
    ("", None),
    ("Required columns", None),
    ("  Pump Tag", "Must match (or normalize to) a canonical pump tag already in the pump master."),
    ("  Frequency", "One of the accepted values below."),
    ("  Start Date", "A real Excel date cell, or text as YYYY-MM-DD or DD/MM/YYYY. MM/DD/YYYY-shaped text is rejected as ambiguous."),
    ("", None),
    ("Optional columns", None),
    ("  Planned Activities", "Semicolon-separated canonical activity labels (see below). Leave blank for none."),
    ("  Assigned Technician", None),
    ("  Estimated Duration", "Hours, zero or more."),
    ("  Notes", None),
    ("", None),
    ("Accepted Frequency values", None),
    ("  DAILY", "Daily, Harian"),
    ("  WEEKLY", "Weekly, Mingguan"),
    ("  MONTHLY", "Monthly, Bulanan"),
    ("  RUNTIME_BASED", "Runtime Based, Runtime-Based, Runtime, Operating Hours"),
    ("", None),
    ("Planned Activities syntax", None),
    ("  Example:", "Flushing Line DE; Quench Line General; Cooler DE; Cooler NDE"),
    ("  Accepted labels:", None),
    ("    Flushing Line General / DE / NDE", None),
    ("    Quench Line General / DE / NDE", None),
    ("    Strainer General / DE / NDE", None),
    ("    Check Valve General / DE / NDE", None),
    ("    Reservoir General", "Reservoir has no DE/NDE variant -- General only."),
    ("    Cooler General / DE / NDE", "Cooler is a different piece of equipment from Cooling Water Cooler below -- never the same row."),
    ("    Cooling Water Cooler General / DE / NDE", None),
    ("", None),
    ("Notes", None),
    ("  Schedule Code, Status, Trigger Type, Procedure, and Checklist Template", "are system-managed and must not be included in this file."),
)


def build_pm_schedule_import_template() -> bytes:
    workbook = Workbook()

    data_sheet = workbook.active
    data_sheet.title = "PM Schedule Import"
    data_sheet.append([escape_formula_leading(c) for c in TEMPLATE_COLUMNS])
    # Section O -- header row frozen; data rows deliberately left empty
    # (the mission's own permitted alternative to example rows) so a
    # user can never accidentally submit a placeholder row as real data.
    data_sheet.freeze_panes = "A2"

    instructions_sheet = workbook.create_sheet("Instructions")
    for label, detail in _INSTRUCTIONS:
        row = [escape_formula_leading(label)]
        if detail is not None:
            row.append(escape_formula_leading(detail))
        instructions_sheet.append(row)
    instructions_sheet.column_dimensions["A"].width = 40
    instructions_sheet.column_dimensions["B"].width = 70

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


__all__ = ["build_pm_schedule_import_template", "escape_formula_leading", "TEMPLATE_COLUMNS"]
