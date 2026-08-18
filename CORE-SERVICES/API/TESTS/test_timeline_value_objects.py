import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource


def test_timeline_category_has_all_canonical_categories():
    # Stale name/assertion fixed in passing (MWO-LTSA-PM-CM-INTAKE-001):
    # this test already diverged from the real, committed 11-member
    # TimelineCategory enum before this MWO touched anything (confirmed
    # via a prior session's own investigation) -- brought back in sync
    # while this same file is already being edited for TimelineSource
    # below, not a separate opportunistic pass.
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
    # MWO-LTSA-PM-CM-INTAKE-001 -- CONDITION_MONITORING_READING added:
    # TimelineCategory.INSPECTION is now really populated from
    # condition_monitoring_reading (equipment_timeline_service.py's
    # _build_inspection_events), not left as a permanently-empty
    # declared-but-unpopulated category. INSTALLATION_REPORT/WORK_ORDER/
    # SEAL_REGISTRY were already real, committed members this test had
    # never been updated to include either.
    assert {member.value for member in TimelineSource} == {
        "PM_OCCURRENCE",
        "CM_REPORT",
        "MAINTENANCE_HISTORY",
        "INSTALLATION_REPORT",
        "WORK_ORDER",
        "SEAL_REGISTRY",
        "CONDITION_MONITORING_READING",
        "UNKNOWN",
    }
