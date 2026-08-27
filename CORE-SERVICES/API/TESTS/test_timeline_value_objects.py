import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource


def test_timeline_category_has_all_canonical_categories():
    # MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B -- re-synced again: this
    # test had already gone stale once (fixed under MWO-LTSA-PM-CM-
    # INTAKE-001 for the first 11 members) and then diverged a second
    # time when MWO-LTSA-SEAL-EQUIPMENT-HISTORY-INTEGRATION-001 added the
    # 7 physical-mechanical-seal categories (timeline_value_objects.py's
    # own header comment on that MWO). Both drifts were real, committed
    # enum members this test simply hadn't been updated to include.
    assert {member.value for member in TimelineCategory} == {
        "PM",
        "CM",
        "INSTALLATION",
        "FAILURE",
        "WORK_ORDER",
        "REPLACEMENT",
        "BREAKDOWN",
        "SEAL_REPLACEMENT",
        "INSPECTION",
        "INVENTORY_EVENT",
        "RECOMMENDATION",
        "SEAL_INSTALL",
        "SEAL_REMOVE",
        "SEAL_INSPECTION",
        "SEAL_REPAIR",
        "SEAL_RETURN_TO_STOCK",
        "SEAL_SCRAP",
        "SEAL_WARRANTY",
    }


def test_timeline_category_members_are_strings():
    assert TimelineCategory.PM == "PM"
    assert isinstance(TimelineCategory.PM, str)


def test_timeline_severity_mirrors_existing_cm_report_vocabulary():
    # ADR-CM-001's own real severity vocabulary (MINOR/MODERATE/MAJOR/
    # CRITICAL) plus UNKNOWN for categories/records with no severity
    # concept -- not an invented scale.
    assert {member.value for member in TimelineSeverity} == {
        "UNKNOWN",
        "MINOR",
        "MODERATE",
        "MAJOR",
        "CRITICAL",
    }


def test_timeline_source_has_only_real_gateway_backed_sources():
    # MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B -- re-synced again: 4 more
    # real, committed sources (SEAL_LIFECYCLE_EVENT, SEAL_INSPECTION,
    # SEAL_REPAIR, SEAL_WARRANTY_ASSESSMENT) were added by MWO-LTSA-SEAL-
    # EQUIPMENT-HISTORY-INTEGRATION-001 to back the 7 new SEAL_* categories
    # (see test_timeline_category_has_all_canonical_categories above),
    # after this assertion was last updated under MWO-LTSA-PM-CM-INTAKE-001.
    assert {member.value for member in TimelineSource} == {
        "PM_OCCURRENCE",
        "CM_REPORT",
        "MAINTENANCE_HISTORY",
        "INSTALLATION_REPORT",
        "WORK_ORDER",
        "SEAL_REGISTRY",
        "CONDITION_MONITORING_READING",
        "SEAL_LIFECYCLE_EVENT",
        "SEAL_INSPECTION",
        "SEAL_REPAIR",
        "SEAL_WARRANTY_ASSESSMENT",
        "UNKNOWN",
    }
