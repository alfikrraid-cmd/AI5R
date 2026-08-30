"""MWO-LTSA-CMON-DETAILED-HISTORY-001 -- Python-side mirror of
AI5R-STUDIO/dashboard/src/modules/ltsa/utils/conditionMonitoringMeasurementFields.js,
the established single source of truth for CMON measurement field labels
and units. Column list matches condition_monitoring_reading_repository.py's
own exported _MEASUREMENT_COLUMNS exactly (reused, not re-derived); labels
and units are ported unchanged from that JS module's own already-disclosed
convention (°C / bar / mm/s / A -- ConditionMonitoringReadingDetailPanel.jsx's
own tempValue/pressureValue/vibrationValue formatting), never invented
here. Backend has no prior Python-side copy of this mapping; this module
exists so a WhatsApp/copilot response can render the SAME parameter
labels/units the dashboard already shows for the exact same canonical
columns, not a second, divergent vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MeasurementPairField:
    label: str
    de_column: str
    nde_column: str
    unit: str


@dataclass(frozen=True, slots=True)
class MeasurementSingleField:
    label: str
    column: str
    unit: str


# MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001's own DE/NDE pairs, ported
# 1:1 (group -> label, deColumn/ndeColumn -> de_column/nde_column, unit
# unchanged).
MEASUREMENT_PAIR_FIELDS: tuple[MeasurementPairField, ...] = (
    MeasurementPairField("Mechanical Seal Temp", "mechseal_temp_de", "mechseal_temp_nde", "°C"),
    MeasurementPairField("Flushing Temp", "flushing_temp_de", "flushing_temp_nde", "°C"),
    MeasurementPairField("Quench Temp", "quench_temp_de", "quench_temp_nde", "°C"),
    MeasurementPairField("Flushing In Temp (LBI)", "flushing_in_temp_de", "flushing_in_temp_nde", "°C"),
    MeasurementPairField("Flushing Out Temp (LBO)", "flushing_out_temp_de", "flushing_out_temp_nde", "°C"),
    MeasurementPairField("Cooling Water In Temp", "cooling_water_in_temp_de", "cooling_water_in_temp_nde", "°C"),
    MeasurementPairField("Cooling Water Out Temp", "cooling_water_out_temp_de", "cooling_water_out_temp_nde", "°C"),
    MeasurementPairField("Water Jacket Temp", "water_jacket_temp_de", "water_jacket_temp_nde", "°C"),
    MeasurementPairField("Quench Pressure", "quench_pressure_de", "quench_pressure_nde", "bar"),
    MeasurementPairField("Stuffing Box Temp", "stuffing_box_temp_de", "stuffing_box_temp_nde", "°C"),
    MeasurementPairField("Seal Gland Temp", "seal_gland_temp_de", "seal_gland_temp_nde", "°C"),
    MeasurementPairField("Vertical Vibration", "vertical_vibration_de", "vertical_vibration_nde", "mm/s"),
    MeasurementPairField("Horizontal Vibration", "horizontal_vibration_de", "horizontal_vibration_nde", "mm/s"),
    MeasurementPairField("Axial Vibration", "axial_vibration_de", "axial_vibration_nde", "mm/s"),
    MeasurementPairField("Bearing Temp", "bearing_temp_de", "bearing_temp_nde", "°C"),
)

MEASUREMENT_SINGLE_FIELDS: tuple[MeasurementSingleField, ...] = (
    MeasurementSingleField("Suction Temp", "suction_temp", "°C"),
    MeasurementSingleField("Discharge Temp", "discharge_temp", "°C"),
    MeasurementSingleField("Suction Pressure", "suction_pressure", "bar"),
    MeasurementSingleField("Discharge Pressure", "discharge_pressure", "bar"),
    MeasurementSingleField("Motor Current", "motor_current", "A"),
)

LEAK_FIELD_DE = "mechanical_seal_leak_de"
LEAK_FIELD_NDE = "mechanical_seal_leak_nde"


def _leak_display(value: Any) -> str | None:
    if value is True:
        return "Leak detected"
    if value is False:
        return "No leak"
    return None  # not recorded -- tri-state, never coerced to "No leak"


def render_reading_lines(record: dict[str, Any]) -> list[str]:
    """Every non-null measurement value on this one CMON event, as
    "label: value unit" lines -- ONLY fields actually present (non-None)
    in the canonical record, never a fixed list padded with fabricated
    values. pump_operating_state (a TEXT field, not DE/NDE, not a unit-
    bearing measurement) is included as its own line when present."""
    lines: list[str] = []
    for field in MEASUREMENT_PAIR_FIELDS:
        de_value = record.get(field.de_column)
        nde_value = record.get(field.nde_column)
        if de_value is not None:
            lines.append(f"{field.label} DE: {de_value} {field.unit}")
        if nde_value is not None:
            lines.append(f"{field.label} NDE: {nde_value} {field.unit}")
    for field in MEASUREMENT_SINGLE_FIELDS:
        value = record.get(field.column)
        if value is not None:
            lines.append(f"{field.label}: {value} {field.unit}")
    leak_de = _leak_display(record.get(LEAK_FIELD_DE))
    if leak_de is not None:
        lines.append(f"Mechanical Seal Leak DE: {leak_de}")
    leak_nde = _leak_display(record.get(LEAK_FIELD_NDE))
    if leak_nde is not None:
        lines.append(f"Mechanical Seal Leak NDE: {leak_nde}")
    operating_state = record.get("pump_operating_state")
    if operating_state:
        lines.append(f"Pump Operating State: {operating_state}")
    return lines


# MWO-LTSA-EQUIPMENT-360-CANONICAL-001 -- generic parameter-level lookup
# (Phase 6): a user word ("temperature"/"suhu"/"vibration"/"getaran"/
# "pressure"/"tekanan") maps to a SEARCH TERM matched against each field's
# own label (e.g. "temp" matches every "...Temp" field -- Mechanical Seal
# Temp, Flushing Temp, Bearing Temp, Suction Temp, etc., all genuinely
# temperature fields per this module's own MEASUREMENT_PAIR_FIELDS/
# MEASUREMENT_SINGLE_FIELDS list). New canonical parameters therefore work
# automatically as their label already contains the matched term -- no new
# intent handler needed per parameter, per this MWO's own explicit
# requirement. "current"/"arus" is deliberately NOT included here: it
# collides with this module's sibling _detect_intent's own pre-existing
# "current"/is_current_or_latest wording ("current seal", "seal saat
# ini") -- adding it would misroute an unrelated current-seal question
# into a Motor Current parameter lookup. Motor Current remains reachable
# only via its own field label match if a caller passes "motor current"
# directly, never via the single ambiguous word "current".
_PARAMETER_SEARCH_TERMS: dict[str, str] = {
    "temperature": "temp",
    "suhu": "temp",
    # MWO-LTSA-FLEET-ANALYTICS-001 -- "temperatur" (no final "e") is the
    # common Indonesian technical spelling ("temperaturnya paling
    # tinggi?") and is NOT a substring of "temperature" -- a genuinely
    # separate word, not covered by the \w* suffix-agglutination fix
    # below.
    "temperatur": "temp",
    "vibration": "vibration",
    "getaran": "vibration",
    "pressure": "pressure",
    "tekanan": "pressure",
    "motor current": "current",
}


_SEARCH_TERM_DISPLAY_LABEL = {
    "temp": "Temperature",
    "vibration": "Vibration",
    "pressure": "Pressure",
    "current": "Motor Current",
}


def parameter_display_label(term: str) -> str:
    """The GENERIC label for a search term (e.g. "temp" -> "Temperature")
    -- used as the response header, since the specific matched field
    (Bearing Temp, Mechanical Seal Temp, ...) varies per record and must
    never be presented as if it were the only/defining one."""
    return _SEARCH_TERM_DISPLAY_LABEL.get(term, term.capitalize())


def detect_parameter_search_term(text: str) -> str | None:
    """Returns the search term (e.g. "temp") for the first recognized
    parameter word found in `text`, or None if no parameter word is
    present. Word-boundary matched at the START of the word, case-
    insensitive -- \\w* after the literal word (MWO-LTSA-FLEET-ANALYTICS-
    001) allows an agglutinated Indonesian suffix ("suhunya",
    "vibrationnya", "getarannya") to still match, since a strict trailing
    \\b would otherwise fail (the suffix's first letter is itself a word
    character, so no boundary exists there)."""
    lowered = (text or "").casefold()
    for word, term in _PARAMETER_SEARCH_TERMS.items():
        if re.search(r"\b" + re.escape(word) + r"\w*\b", lowered):
            return term
    return None


def fields_matching_search_term(term: str) -> list[MeasurementPairField | MeasurementSingleField]:
    """Every canonical field (pair or single) whose own label contains
    `term` -- the SAME MEASUREMENT_PAIR_FIELDS/MEASUREMENT_SINGLE_FIELDS
    list used everywhere else in this module, no separate parameter
    registry to drift out of sync."""
    lowered_term = term.casefold()
    matches: list[MeasurementPairField | MeasurementSingleField] = [
        field for field in MEASUREMENT_PAIR_FIELDS if lowered_term in field.label.casefold()
    ]
    matches += [field for field in MEASUREMENT_SINGLE_FIELDS if lowered_term in field.label.casefold()]
    return matches


def render_parameter_lines(record: dict[str, Any], fields: list[Any]) -> list[str]:
    """Same non-null-only rendering discipline as render_reading_lines,
    restricted to the given (already parameter-filtered) field list."""
    lines: list[str] = []
    for field in fields:
        if isinstance(field, MeasurementPairField):
            de_value = record.get(field.de_column)
            nde_value = record.get(field.nde_column)
            if de_value is not None:
                lines.append(f"{field.label} DE: {de_value} {field.unit}")
            if nde_value is not None:
                lines.append(f"{field.label} NDE: {nde_value} {field.unit}")
        else:
            value = record.get(field.column)
            if value is not None:
                lines.append(f"{field.label}: {value} {field.unit}")
    return lines


def parameter_values(record: dict[str, Any], fields: list[Any]) -> list[tuple[str, float, str]]:
    """(label, numeric_value, unit) for every non-null value of the given
    fields on this one record -- the raw numbers a deterministic min/max/
    trend calculation needs, never text formatting."""
    values: list[tuple[str, float, str]] = []
    for field in fields:
        if isinstance(field, MeasurementPairField):
            de_value = record.get(field.de_column)
            nde_value = record.get(field.nde_column)
            if de_value is not None:
                values.append((f"{field.label} DE", de_value, field.unit))
            if nde_value is not None:
                values.append((f"{field.label} NDE", nde_value, field.unit))
        else:
            value = record.get(field.column)
            if value is not None:
                values.append((field.label, value, field.unit))
    return values


__all__ = [
    "MeasurementPairField",
    "MeasurementSingleField",
    "MEASUREMENT_PAIR_FIELDS",
    "MEASUREMENT_SINGLE_FIELDS",
    "LEAK_FIELD_DE",
    "LEAK_FIELD_NDE",
    "render_reading_lines",
    "detect_parameter_search_term",
    "fields_matching_search_term",
    "render_parameter_lines",
    "parameter_values",
]
