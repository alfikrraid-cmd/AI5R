"""
MWO-LTSA-031B-R1 -- canonical Timeline value objects. Repository
archaeology confirmed no TimelineCategory/TimelineSeverity/TimelineSource
(or equivalent) exists anywhere in the repository -- CORE-SERVICES has no
prior `enum.Enum` usage at all (its existing closed vocabularies, e.g.
engineering_context_engine.py's OPEN_CM_REPORT_STATUSES, are plain
frozenset[str] constants). AI5R-SDK does establish a `class X(str, Enum)`
convention (e.g. CORE/artifact_status.py) -- followed here for style,
without introducing a new CORE-SERVICES -> AI5R-SDK dependency edge.

TimelineSeverity mirrors ADR-CM-001's own real, already-stored cm_report
severity vocabulary (MINOR/MODERATE/MAJOR/CRITICAL) plus UNKNOWN -- not
an invented scale. TimelineSource lists only gateways that actually back
a populated Timeline category today (PM_OCCURRENCE, CM_REPORT,
MAINTENANCE_HISTORY) plus UNKNOWN as the fallback for any category with
no backing gateway yet -- no source name is invented for Seal
Replacement, Inspection, Inventory Event, or Recommendation, since none
of those has a real gateway to name.
"""

from __future__ import annotations

from enum import Enum


class TimelineCategory(str, Enum):
    """The 7 canonical Timeline categories, per Chief Architect decision
    (MWO-LTSA-031B-R1). All 7 are canonical regardless of whether a
    category currently has any populated events."""

    PM = "PM"
    CM = "CM"
    INSTALLATION = "INSTALLATION"
    FAILURE = "FAILURE"
    WORK_ORDER = "WORK_ORDER"
    REPLACEMENT = "REPLACEMENT"
    BREAKDOWN = "BREAKDOWN"
    SEAL_REPLACEMENT = "SEAL_REPLACEMENT"
    INSPECTION = "INSPECTION"
    INVENTORY_EVENT = "INVENTORY_EVENT"
    RECOMMENDATION = "RECOMMENDATION"


class TimelineSeverity(str, Enum):
    """Mirrors ADR-CM-001's real cm_report.severity vocabulary, plus
    UNKNOWN for events/categories with no severity concept."""

    UNKNOWN = "UNKNOWN"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class TimelineSource(str, Enum):
    """The Gateway/domain each populated category's data actually comes
    from, plus UNKNOWN for any category with no backing gateway yet."""

    PM_OCCURRENCE = "PM_OCCURRENCE"
    CM_REPORT = "CM_REPORT"
    MAINTENANCE_HISTORY = "MAINTENANCE_HISTORY"
    INSTALLATION_REPORT = "INSTALLATION_REPORT"
    WORK_ORDER = "WORK_ORDER"
    SEAL_REGISTRY = "SEAL_REGISTRY"
    # MWO-LTSA-PM-CM-INTAKE-001 -- backs TimelineCategory.INSPECTION,
    # now populated from condition_monitoring_reading (never cm_report --
    # see ADR-CONDITION-MONITORING-001's own "CMON, never a bare CM").
    CONDITION_MONITORING_READING = "CONDITION_MONITORING_READING"
    UNKNOWN = "UNKNOWN"


__all__ = ["TimelineCategory", "TimelineSeverity", "TimelineSource"]
