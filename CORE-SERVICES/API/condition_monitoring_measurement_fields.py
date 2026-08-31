from __future__ import annotations

from typing import Any, Iterable

_TEMPERATURE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("flushing_temp_de", "flushing_temp_de", "degC"),
    ("flushing_temp_nde", "flushing_temp_nde", "degC"),
    ("quench_temp_de", "quench_temp_de", "degC"),
    ("quench_temp_nde", "quench_temp_nde", "degC"),
    ("flushing_in_temp_de", "flushing_in_temp_de", "degC"),
    ("flushing_in_temp_nde", "flushing_in_temp_nde", "degC"),
    ("flushing_out_temp_de", "flushing_out_temp_de", "degC"),
    ("flushing_out_temp_nde", "flushing_out_temp_nde", "degC"),
    ("cooling_water_in_temp_de", "cooling_water_in_temp_de", "degC"),
    ("cooling_water_in_temp_nde", "cooling_water_in_temp_nde", "degC"),
    ("cooling_water_out_temp_de", "cooling_water_out_temp_de", "degC"),
    ("cooling_water_out_temp_nde", "cooling_water_out_temp_nde", "degC"),
    ("mechseal_temp_de", "mechseal_temp_de", "degC"),
    ("mechseal_temp_nde", "mechseal_temp_nde", "degC"),
    ("water_jacket_temp_de", "water_jacket_temp_de", "degC"),
    ("water_jacket_temp_nde", "water_jacket_temp_nde", "degC"),
    ("suction_temp", "suction_temp", "degC"),
    ("discharge_temp", "discharge_temp", "degC"),
    ("stuffing_box_temp_de", "stuffing_box_temp_de", "degC"),
    ("stuffing_box_temp_nde", "stuffing_box_temp_nde", "degC"),
    ("seal_gland_temp_de", "seal_gland_temp_de", "degC"),
    ("seal_gland_temp_nde", "seal_gland_temp_nde", "degC"),
    ("bearing_temp_de", "bearing_temp_de", "degC"),
    ("bearing_temp_nde", "bearing_temp_nde", "degC"),
)

_VIBRATION_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("vertical_vibration_de", "vertical_vibration_de", "mm/s"),
    ("vertical_vibration_nde", "vertical_vibration_nde", "mm/s"),
    ("horizontal_vibration_de", "horizontal_vibration_de", "mm/s"),
    ("horizontal_vibration_nde", "horizontal_vibration_nde", "mm/s"),
    ("axial_vibration_de", "axial_vibration_de", "mm/s"),
    ("axial_vibration_nde", "axial_vibration_nde", "mm/s"),
)


def fields_matching_search_term(term: str) -> tuple[tuple[str, str, str], ...]:
    normalized = (term or "").lower()
    if "vib" in normalized:
        return _VIBRATION_FIELDS
    if "temp" in normalized:
        return _TEMPERATURE_FIELDS
    return ()


def parameter_values(record: dict[str, Any], fields: Iterable[tuple[str, str, str]]) -> tuple[tuple[str, Any, str], ...]:
    values = []
    for field_name, label, unit in fields:
        value = record.get(field_name)
        if value is not None:
            values.append((label, value, unit))
    return tuple(values)


__all__ = ["fields_matching_search_term", "parameter_values"]
