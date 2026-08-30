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


__all__ = [
    "MeasurementPairField",
    "MeasurementSingleField",
    "MEASUREMENT_PAIR_FIELDS",
    "MEASUREMENT_SINGLE_FIELDS",
    "LEAK_FIELD_DE",
    "LEAK_FIELD_NDE",
    "render_reading_lines",
]
