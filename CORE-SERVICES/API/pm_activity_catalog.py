"""MWO-LTSA-PM-SCHEDULE-FOUNDATION-4E1 -- canonical PM activity taxonomy,
backend copy of AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pmActivityCatalog.js's
own PM_ACTIVITY_FAMILIES (Phase 4D/4C, verified against 540 real historical
PM occurrences). Kept in exact sync with that file -- 7 families, 19
variants, same codes -- so a `pm_schedule.planned_activities` payload can be
validated server-side against the same vocabulary the dashboard renders.

This module validates PLANNED activity selections only (family/variant/code
triples, no `done` flag -- a plan is not execution evidence). It is not used
for, and must never be used for, pm_occurrence.activities (PERFORMED
activities), which has its own, separate, pre-existing, unconstrained JSONB
contract (Phase 4C's own CODE_TRACER finding) -- left untouched by this
module.
"""

from __future__ import annotations

PM_ACTIVITY_FAMILIES: dict[str, dict[str, str | None]] = {
    "Flushing Line": {"GENERAL": "FLUSHING_LINE", "DE": "FLUSHING_LINE_DE", "NDE": "FLUSHING_LINE_NDE"},
    "Quench Line": {"GENERAL": "QUENCH_LINE", "DE": "QUENCH_LINE_DE", "NDE": "QUENCH_LINE_NDE"},
    "Strainer": {"GENERAL": "STRAINER", "DE": "STRAINER_DE", "NDE": "STRAINER_NDE"},
    "Check Valve": {"GENERAL": "CHECK_VALVE", "DE": "CHECK_VALVE_DE", "NDE": "CHECK_VALVE_NDE"},
    # No DE/NDE evidenced anywhere in the 540 -- General only, matching the
    # frontend catalog's own explicit "never given sided variants" rule.
    "Reservoir": {"GENERAL": "RESERVOIR"},
    # "Cooler" and "Cooling Water Cooler" are DISTINCT families (never
    # merged) -- Cooler's internal-only WCH semantic is never surfaced.
    "Cooler": {"GENERAL": "COOLER", "DE": "COOLER_DE", "NDE": "COOLER_NDE"},
    "Cooling Water Cooler": {
        "GENERAL": "COOLING_WATER_COOLER",
        "DE": "COOLING_WATER_COOLER_DE",
        "NDE": "COOLING_WATER_COOLER_NDE",
    },
}

# code -> (family, variant), derived once -- the single source this module's
# own validator reads, never re-walked ad hoc per call.
_CODE_INDEX: dict[str, tuple[str, str]] = {
    code: (family, variant)
    for family, variants in PM_ACTIVITY_FAMILIES.items()
    for variant, code in variants.items()
}


class InvalidPlannedActivityError(ValueError):
    pass


def validate_planned_activities(entries: list[dict] | None) -> list[dict]:
    """Validates a `pm_schedule.planned_activities` candidate payload
    against the canonical catalog above. Returns a normalized list
    (`family`/`variant`/`code`, nothing else -- a `done` key, if present,
    is REJECTED outright, never silently dropped, so a caller cannot
    accidentally smuggle execution-evidence semantics into a plan).
    Duplicate codes are rejected (an explicit selection is made once).
    `None`/empty input is valid (no planned activities selected)."""
    if not entries:
        return []
    if not isinstance(entries, list):
        raise InvalidPlannedActivityError("planned_activities must be a list")

    seen_codes: set[str] = set()
    normalized: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise InvalidPlannedActivityError(f"planned activity entry must be an object: {entry!r}")
        if "done" in entry:
            raise InvalidPlannedActivityError(
                "planned activity entries must not carry a 'done' field -- a plan is not performed-work evidence"
            )
        code = entry.get("code")
        if not isinstance(code, str) or code not in _CODE_INDEX:
            raise InvalidPlannedActivityError(f"unknown planned activity code: {code!r}")
        if code in seen_codes:
            raise InvalidPlannedActivityError(f"duplicate planned activity code: {code!r}")
        seen_codes.add(code)
        family, variant = _CODE_INDEX[code]
        normalized.append({"family": family, "variant": variant, "code": code})
    return normalized


__all__ = ["PM_ACTIVITY_FAMILIES", "InvalidPlannedActivityError", "validate_planned_activities"]
