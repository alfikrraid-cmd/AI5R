"""MWO-LTSA-CMON-EXCEL-IMPORT-001 -- generates the downloadable
Condition Monitoring Reading Excel import template. Mirrors
pm_schedule_excel_template.py's own shape (2-sheet workbook: data +
Instructions, frozen header row, no example/placeholder data rows), but
columns are derived directly from condition_monitoring_measurement_
fields.py's own MEASUREMENT_PAIR_FIELDS/MEASUREMENT_SINGLE_FIELDS/
LEAK_FIELD_DE/LEAK_FIELD_NDE -- the SAME canonical field list the
backend request model (ConditionMonitoringMeasurements) and the
frontend (conditionMonitoringMeasurementFields.js) already use, so this
template can never list a column the rest of the system doesn't
recognize, or omit one it does.

escape_formula_leading is reused directly from pm_schedule_excel_
template.py, not re-implemented -- it is domain-neutral security
infrastructure (formula-injection escaping), not PM-specific business
logic, so importing it here does not create the CMON-depends-on-PM-
domain-logic coupling this MWO's own Phase 4F.1 discovery explicitly
warned against (that concern is about business rules like pump-tag
normalization or activity taxonomy, which this module never touches).
"""

from __future__ import annotations

import io

from openpyxl import Workbook

from .condition_monitoring_measurement_fields import (
    LEAK_FIELD_DE,
    LEAK_FIELD_NDE,
    MEASUREMENT_PAIR_FIELDS,
    MEASUREMENT_SINGLE_FIELDS,
)
from .pm_schedule_excel_template import escape_formula_leading

LEAK_LABEL = "Mechanical Seal Leak"


def _build_template_columns() -> tuple[str, ...]:
    columns: list[str] = ["Pump Tag *", "Reading Date *"]
    for field in MEASUREMENT_PAIR_FIELDS:
        columns.append(f"{field.label} DE")
        columns.append(f"{field.label} NDE")
    for field in MEASUREMENT_SINGLE_FIELDS:
        columns.append(field.label)
    columns.append(f"{LEAK_LABEL} DE")
    columns.append(f"{LEAK_LABEL} NDE")
    columns.append("Pump Operating State")
    columns.append("Finding / Notes")
    return tuple(columns)


TEMPLATE_COLUMNS = _build_template_columns()


def _instructions() -> tuple[tuple[str, str | None], ...]:
    lines: list[tuple[str, str | None]] = [
        ("Condition Monitoring Reading Import -- Instructions", None),
        ("", None),
        ("Required columns", None),
        ("  Pump Tag", "Must match (or normalize to) a canonical pump tag already in the pump master."),
        ("  Reading Date", "A real Excel date cell, or text as YYYY-MM-DD or DD/MM/YYYY. MM/DD/YYYY-shaped text is rejected as ambiguous."),
        ("", None),
        ("Measurement columns", None),
        ("  Blank", "Not recorded -- never treated as zero or 'not applicable'."),
        ("  Numeric value", "Recorded as-is, including 0 (a legitimate explicit reading)."),
        ("  DE / NDE", "Always independent -- recording one side never implies or requires the other."),
        ("  General", "Not supported -- every sided Condition Monitoring measurement is DE/NDE only."),
        ("", None),
        (f"{LEAK_LABEL} DE / NDE", None),
        ("  Blank / Not Recorded", "Not recorded (kept as NULL, never coerced to No Leak)."),
        ("  No Leak / False / No / 0", "No leak observed."),
        ("  Leak Detected / True / Yes / 1 / Leak", "A leak was observed."),
        ("  Any other value", "Rejected as an error, row retained for correction."),
        ("", None),
        ("Notes", None),
        ("  Reading Code, Provenance, Workflow Status", "are system-managed and must not be included in this file."),
    ]
    return tuple(lines)


def build_condition_monitoring_import_template() -> bytes:
    workbook = Workbook()

    data_sheet = workbook.active
    data_sheet.title = "Readings"
    data_sheet.append([escape_formula_leading(c) for c in TEMPLATE_COLUMNS])
    data_sheet.freeze_panes = "A2"

    instructions_sheet = workbook.create_sheet("Instructions")
    for label, detail in _instructions():
        row = [escape_formula_leading(label)]
        if detail is not None:
            row.append(escape_formula_leading(detail))
        instructions_sheet.append(row)
    instructions_sheet.column_dimensions["A"].width = 40
    instructions_sheet.column_dimensions["B"].width = 70

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


__all__ = ["build_condition_monitoring_import_template", "TEMPLATE_COLUMNS", "LEAK_LABEL"]
