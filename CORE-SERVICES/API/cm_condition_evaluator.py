"""Pure LTSA CM latest-reading selection and condition evaluation.

LTSA_CM_UI_REMEDIATION_R1A -- canonical leak / Current Condition semantics.

Occurrence leak state (DE and NDE are independent tri-states; true dominates;
null is never coerced to false):

    LEAK_DE_AND_NDE, LEAK_DE, LEAK_NDE   -- a leak was recorded on that side
    NO_LEAK                              -- both sides explicitly false
    NO_LEAK_DE_ONLY, NO_LEAK_NDE_ONLY    -- one side false, the other not
                                            recorded (PARTIAL, not NO_LEAK)
    UNKNOWN                              -- neither side recorded

Current Condition = the leak state of the LATEST VALID occurrence, where
valid means workflow SUBMITTED/FINALIZED (CURRENT_CONDITION_STATUSES), live,
dated, asset-bound and carrying at least one observation. No fallback to an
older occurrence, and provenance never influences selection.

The recent-window rule (maintenance_intelligence_service.
leak_flag_from_readings) answers a different question -- RECENT_LEAK_OBSERVED,
"was a leak observed in the last N days" -- and is not Current Condition.

Compatibility (R1A migrates no consumer): ELIGIBLE_STATUSES (which still
includes DRAFT), select_latest_valid_cm()'s default and evaluate_leak()'s
"status" names are unchanged for the existing equipment_360_service caller.
R1B moves Current Condition consumers onto current_leak_condition().
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Iterable


# Legacy latest-reading eligibility (equipment_360_service.cmon_latest).
ELIGIBLE_STATUSES = frozenset({"DRAFT", "SUBMITTED", "FINALIZED"})
# Authoritative Current Condition eligibility: DRAFT is work in progress.
CURRENT_CONDITION_STATUSES = frozenset({"SUBMITTED", "FINALIZED"})

LEAK_DE_AND_NDE = "LEAK_DE_AND_NDE"
LEAK_DE = "LEAK_DE"
LEAK_NDE = "LEAK_NDE"
NO_LEAK = "NO_LEAK"
NO_LEAK_DE_ONLY = "NO_LEAK_DE_ONLY"
NO_LEAK_NDE_ONLY = "NO_LEAK_NDE_ONLY"
UNKNOWN = "UNKNOWN"
LEAK_STATES = (LEAK_DE_AND_NDE, LEAK_DE, LEAK_NDE, NO_LEAK, NO_LEAK_DE_ONLY, NO_LEAK_NDE_ONLY, UNKNOWN)
ACTIVE_LEAK_STATES = frozenset({LEAK_DE_AND_NDE, LEAK_DE, LEAK_NDE})

# evaluate_leak()'s pre-R1A "status" vocabulary, kept for existing callers.
_LEGACY_STATUS = {
    LEAK_DE_AND_NDE: "LEAK_DE_NDE",
    LEAK_DE: "LEAK_DE",
    LEAK_NDE: "LEAK_NDE",
    NO_LEAK: "NO_LEAK",
    NO_LEAK_DE_ONLY: "NO_LEAK_DE",
    NO_LEAK_NDE_ONLY: "NO_LEAK_NDE",
    UNKNOWN: "NOT_RECORDED",
}

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


def _instant(value: Any) -> datetime | None:
    """A comparable naive-UTC datetime for a date/timestamp value, or None.
    Accepts date, datetime and ISO text ("2026-06-12", "2026-06-12 00:00:00",
    "2026-06-12T01:00:00Z"), so mixed representations order by time, not by
    their text."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def is_latest_valid_cm(reading: dict[str, Any], statuses: Iterable[str] = ELIGIBLE_STATUSES) -> bool:
    return (
        reading.get("workflow_status") in frozenset(statuses)
        and not reading.get("deleted_at")
        and _instant(reading.get("reading_date")) is not None
        and bool(reading.get("asset_code"))
        and has_meaningful_observation(reading)
    )


def is_current_condition_candidate(reading: dict[str, Any]) -> bool:
    return is_latest_valid_cm(reading, CURRENT_CONDITION_STATUSES)


def _order_key(reading: dict[str, Any]) -> tuple[datetime, datetime, str]:
    # reading_date DESC, then created_at DESC, then reading code DESC (via max).
    # Provenance is deliberately not part of the key.
    return (
        _instant(reading.get("reading_date")) or datetime.min,
        _instant(reading.get("created_at")) or datetime.min,
        str(reading.get("condition_monitoring_reading_code") or ""),
    )


def select_latest_valid_cm(
    readings: list[dict[str, Any]], *, statuses: Iterable[str] = ELIGIBLE_STATUSES
) -> dict[str, Any] | None:
    valid = [reading for reading in readings if is_latest_valid_cm(reading, statuses)]
    return max(valid, key=_order_key) if valid else None


def select_current_condition_cm(readings: list[dict[str, Any]]) -> dict[str, Any] | None:
    return select_latest_valid_cm(readings, statuses=CURRENT_CONDITION_STATUSES)


def canonical_leak_state(de: bool | None, nde: bool | None) -> str:
    """Occurrence leak state. Only the literal True / False count as recorded;
    anything else (None, "", 0, "Y") is not recorded."""
    de_leak, nde_leak = de is True, nde is True
    if de_leak and nde_leak:
        return LEAK_DE_AND_NDE
    if de_leak:
        return LEAK_DE
    if nde_leak:
        return LEAK_NDE
    de_clear, nde_clear = de is False, nde is False
    if de_clear and nde_clear:
        return NO_LEAK
    if de_clear:
        return NO_LEAK_DE_ONLY
    if nde_clear:
        return NO_LEAK_NDE_ONLY
    return UNKNOWN


def is_active_leak(state: str) -> bool:
    return state in ACTIVE_LEAK_STATES


def evaluate_leak(de: bool | None, nde: bool | None) -> dict[str, Any]:
    state = canonical_leak_state(de, nde)
    de_recorded, nde_recorded = isinstance(de, bool), isinstance(nde, bool)
    completeness = "COMPLETE" if de_recorded and nde_recorded else "PARTIAL" if de_recorded or nde_recorded else "NOT_RECORDED"
    return {
        "status": _LEGACY_STATUS[state],
        "state": state,
        "active": is_active_leak(state),
        "de": de,
        "nde": nde,
        "completeness": completeness,
    }


def current_leak_condition(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Authoritative Current Condition leak for one asset's readings: the
    latest SUBMITTED/FINALIZED valid occurrence decides. With none, the state
    is UNKNOWN and not active -- never an older leaking occurrence."""
    latest = select_current_condition_cm(readings)
    if latest is None:
        return {
            "reading_code": None, "reading_date": None, "workflow_status": None,
            "state": UNKNOWN, "active": False, "de": None, "nde": None,
            "completeness": "NOT_RECORDED", "has_current_reading": False,
        }
    leak = evaluate_leak(latest.get("mechanical_seal_leak_de"), latest.get("mechanical_seal_leak_nde"))
    return {
        "reading_code": latest.get("condition_monitoring_reading_code"),
        "reading_date": latest.get("reading_date"),
        "workflow_status": latest.get("workflow_status"),
        "state": leak["state"],
        "active": leak["active"],
        "de": leak["de"],
        "nde": leak["nde"],
        "completeness": leak["completeness"],
        "has_current_reading": True,
    }


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


__all__ = [
    "ACTIVE_LEAK_STATES", "CURRENT_CONDITION_STATUSES", "ELIGIBLE_STATUSES", "LEAK_STATES",
    "LEAK_DE_AND_NDE", "LEAK_DE", "LEAK_NDE", "NO_LEAK", "NO_LEAK_DE_ONLY", "NO_LEAK_NDE_ONLY", "UNKNOWN",
    "canonical_leak_state", "current_leak_condition", "evaluate_current_condition", "evaluate_leak",
    "has_meaningful_observation", "is_active_leak", "is_current_condition_candidate", "is_latest_valid_cm",
    "select_current_condition_cm", "select_latest_valid_cm",
]
