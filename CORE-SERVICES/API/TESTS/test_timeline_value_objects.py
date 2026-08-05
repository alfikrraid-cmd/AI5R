import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.timeline_value_objects import TimelineCategory, TimelineSeverity, TimelineSource


def test_timeline_category_has_all_seven_canonical_categories():
    assert {member.value for member in TimelineCategory} == {
        "PM",
        "CM",
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
    assert {member.value for member in TimelineSource} == {
        "PM_OCCURRENCE",
        "CM_REPORT",
        "MAINTENANCE_HISTORY",
        "UNKNOWN",
    }
