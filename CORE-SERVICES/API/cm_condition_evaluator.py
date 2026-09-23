"""Pure LTSA CM latest-reading selection and condition evaluation."""

from __future__ import annotations

import re
from typing import Any


ELIGIBLE_STATUSES = frozenset({"DRAFT", "SUBMITTED", "FINALIZED"})
_OBSERVATION_FIELDS = (
    "mechanical_seal_leak_de", "mechanical_seal_leak_nde",
    "mechseal_temp_de", "mechseal_temp_nde",
    "flushing_temp_de", "flushing_temp_nde", "flushing_in_temp_de", "flushing_in_temp_nde",
    "flushing_out_temp_de", "flushing_out_temp_nde",
    "quench_temp_de", "quench_temp_nde", "quench_pressure_de", "quench_pressure_nde",
    "cooling_water_in_temp_de", "cooling_water_in_temp_nde",
    "cooling_water_out_temp_de", "cooling_water_out_temp_nde",
    "water_jacket_temp_de", "water_jacket_temp_nde",
    "suction_temp", "discharge_temp", "suction_pressure", "discharge_pressure",
    "stuffing_box_temp_de", "stuffing_box_temp_nde", "seal_gland_temp_de", "seal_gland_temp_nde",
    "vertical_vibration_de", "vertical_vibration_nde", "horizontal_vibration_de", "horizontal_vibration_nde",
    "axial_vibration_de", "axial_vibration_nde", "bearing_temp_de", "bearing_temp_nde",
    "motor_current", "pump_operating_state",
)
_POSITIVE_FINDING = re.compile(r"(?:bocor|leak(?:ing)?)\b", re.IGNORECASE)
_NEGATED_FINDING = re.compile(r"\b(?:tidak\s+(?:ada\s+)?|no\s+|not\s+)(?:bocor|leak(?:ing)?)\b", re.IGNORECASE)


def has_meaningful_observation(reading: dict[str, Any]) -> bool:
    return any(reading.get(field) is not None for field in _OBSERVATION_FIELDS)


def is_latest_valid_cm(reading: dict[str, Any]) -> bool:
    return (
        reading.get("workflow_status") in ELIGIBLE_STATUSES
        and not reading.get("deleted_at")
        and reading.get("reading_date") is not None
        and bool(reading.get("asset_code"))
        and has_meaningful_observation(reading)
    )


def _order_key(reading: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(reading.get("reading_date") or ""),
        str(reading.get("created_at") or ""),
        str(reading.get("condition_monitoring_reading_code") or ""),
    )


def select_latest_valid_cm(readings: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [reading for reading in readings if is_latest_valid_cm(reading)]
    return max(valid, key=_order_key) if valid else None


def evaluate_leak(de: bool | None, nde: bool | None) -> dict[str, Any]:
    if de is True and nde is True:
        status = "LEAK_DE_NDE"
    elif de is True:
        status = "LEAK_DE"
    elif nde is True:
        status = "LEAK_NDE"
    elif de is False and nde is False:
        status = "NO_LEAK"
    elif de is False:
        status = "NO_LEAK_DE"
    elif nde is False:
        status = "NO_LEAK_NDE"
    else:
        status = "NOT_RECORDED"
    completeness = "COMPLETE" if de is not None and nde is not None else "PARTIAL" if de is not None or nde is not None else "NOT_RECORDED"
    return {"status": status, "de": de, "nde": nde, "completeness": completeness}


def _finding_conflict(reading: dict[str, Any], leak: dict[str, Any]) -> str:
    finding = str(reading.get("finding") or "").strip()
    if leak["status"] == "NO_LEAK" and finding and _POSITIVE_FINDING.search(finding) and not _NEGATED_FINDING.search(finding):
        return "REVIEW_REQUIRED"
    return "NONE"


def evaluate_current_condition(reading: dict[str, Any] | None) -> dict[str, Any] | None:
    if reading is None:
        return None
    leak = evaluate_leak(reading.get("mechanical_seal_leak_de"), reading.get("mechanical_seal_leak_nde"))
    return {
        "asset_code": reading.get("asset_code"),
        "reading_code": reading.get("condition_monitoring_reading_code"),
        "reading_date": reading.get("reading_date"),
        "workflow_status": reading.get("workflow_status"),
        "leak": leak,
        "seal_temperature": {"status": "UNASSESSED", "de": reading.get("mechseal_temp_de"), "nde": reading.get("mechseal_temp_nde")},
        "flushing": {"status": "UNASSESSED", "de": reading.get("flushing_temp_de"), "nde": reading.get("flushing_temp_nde"), "in_de": reading.get("flushing_in_temp_de"), "in_nde": reading.get("flushing_in_temp_nde"), "out_de": reading.get("flushing_out_temp_de"), "out_nde": reading.get("flushing_out_temp_nde")},
        "quench": {"status": "UNASSESSED", "de": reading.get("quench_temp_de"), "nde": reading.get("quench_temp_nde"), "pressure_de": reading.get("quench_pressure_de"), "pressure_nde": reading.get("quench_pressure_nde")},
        "operating_status": reading.get("pump_operating_state"),
        "api_plan_snapshot": reading.get("api_plan_snapshot"),
        "data_quality": "OBSERVED" if has_meaningful_observation(reading) else "NO_MEASUREMENT",
        "finding_conflict": _finding_conflict(reading, leak),
        "finding": reading.get("finding"),
    }


__all__ = ["ELIGIBLE_STATUSES", "evaluate_current_condition", "evaluate_leak", "has_meaningful_observation", "is_latest_valid_cm", "select_latest_valid_cm"]
