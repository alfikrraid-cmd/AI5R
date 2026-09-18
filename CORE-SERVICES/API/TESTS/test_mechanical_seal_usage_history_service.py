"""R2I -- pure-function tests for mechanical_seal_usage_history_service.py.

No DB, no gateway, no fixture derived from the R2C/R2G diagnostic CSVs --
synthetic data only, per the mission's own explicit instruction.
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from mechanical_seal_usage_history_service import (  # noqa: E402
    classify_master_association,
    derive_provenance_status,
    list_pump_seal_usage_history,
    list_seal_usage_history,
    parse_seal_size,
    project_usage_history_event,
)

REGISTRY = [
    {"seal_code": "LTSA-SEAL-T48MP-2-1-8", "seal_name": "T48MP", "shaft_size": 2.125},
    {"seal_code": "LTSA-SEAL-T604-2-7-8", "seal_name": "T604", "shaft_size": 2.875},
    # A second T48MP row at a DIFFERENT size, to prove type-only is never
    # sufficient and exact size still discriminates correctly.
    {"seal_code": "LTSA-SEAL-T48MP-3-1-2", "seal_name": "T48MP", "shaft_size": 3.5},
]


def _installation(**overrides):
    base = {
        "installation_code": "INSTL-100-2026",
        "report_date": "2026-06-08",
        "plant_equip_no": "211-P-8A",
        "pump_tag_number": None,
        "seal_code": None,
        "seal_type": "T48MP",
        "seal_size": '2.1/8"',
    }
    base.update(overrides)
    return base


def test_parse_seal_size_fraction_decimal_and_mm():
    assert parse_seal_size('2.1/8"') == 2.125
    assert parse_seal_size('3"') == 3.0
    assert parse_seal_size("55 MM") == 55.0
    assert parse_seal_size("55 mm") == 55.0


def test_parse_seal_size_never_guesses_compound_or_missing():
    assert parse_seal_size(None) is None
    assert parse_seal_size("-") is None
    assert parse_seal_size("139.70MM/130.10MM") is None


def test_class_a_exact_unique_match():
    result = classify_master_association("T48MP", '2.1/8"', REGISTRY)
    assert result == {"classifier_class": "A", "master_seal_code": "LTSA-SEAL-T48MP-2-1-8", "candidate_count": 1}


def test_class_c_type_matches_but_size_does_not_seal_006_028_pattern():
    # Real R2G evidence: T604 recorded as seal_size='3"' never matches
    # the registry's T604 row at shaft_size=2.875 -- exact match only,
    # never nearest/fuzzy.
    result = classify_master_association("T604", '3"', REGISTRY)
    assert result["classifier_class"] == "C"
    assert result["master_seal_code"] is None


def test_class_d_missing_type():
    result = classify_master_association(None, '2.1/8"', REGISTRY)
    assert result["classifier_class"] == "D"


def test_class_d_missing_or_unparseable_size():
    result = classify_master_association("T48MP", None, REGISTRY)
    assert result["classifier_class"] == "D"
    result2 = classify_master_association("T48MP", "139.70MM/130.10MM", REGISTRY)
    assert result2["classifier_class"] == "D"


def test_class_b_multiple_candidates():
    registry_with_duplicate_size = REGISTRY + [
        {"seal_code": "LTSA-SEAL-T48MP-2-1-8-DUP", "seal_name": "T48MP", "shaft_size": 2.125},
    ]
    result = classify_master_association("T48MP", '2.1/8"', registry_with_duplicate_size)
    assert result["classifier_class"] == "B"
    assert result["master_seal_code"] is None


def test_provenance_clear_when_tags_agree_or_one_is_absent():
    assert derive_provenance_status("211-P-8A", "211-P-8A") == "CLEAR"
    assert derive_provenance_status("211-P-8A", None) == "CLEAR"
    assert derive_provenance_status(None, None) == "CLEAR"


def test_provenance_hold_on_structural_mismatch():
    assert derive_provenance_status("140-P-26B", "140-P-26A") == "HOLD"


def test_confirmed_event_carries_master_seal_code():
    event = project_usage_history_event(_installation(), REGISTRY)
    assert event["master_association_status"] == "CONFIRMED"
    assert event["master_seal_code"] == "LTSA-SEAL-T48MP-2-1-8"
    assert event["master_association_approvable"] is True


def test_provenance_hold_overrides_confirmed_even_with_clean_match():
    # Mirrors R2G's own INSTL-041-2026 finding: clean A-class match, still
    # not approvable once provenance contradicts itself.
    event = project_usage_history_event(
        _installation(plant_equip_no="140-P-26B", pump_tag_number="140-P-26A"),
        REGISTRY,
    )
    assert event["classifier_class"] == "A"
    assert event["master_association_status"] == "PROVENANCE_HOLD"
    assert event["master_association_approvable"] is False
    assert event["review"]["provenance"] == "CONTRADICTION_FOUND"


def test_no_heuristic_intervention_classification_ever():
    # Explicit R2I hard rule -- even with narrative fields present nowhere
    # in the input, intervention_type must always stay UNKNOWN, never
    # inferred from summary/BOM text (which this function never even
    # receives).
    event = project_usage_history_event(_installation(), REGISTRY)
    assert event["intervention_type"] == "UNKNOWN"
    assert event["intervention_actions"] == []
    assert event["review"]["intervention"] == "NOT_DERIVABLE_FROM_STRUCTURED_DATA"
    assert "replaced" not in event["detail"].lower()


def test_physical_unit_never_synthesized():
    event = project_usage_history_event(_installation(), REGISTRY)
    assert event["physical_seal_unit_id"] is None
    assert event["physical_unit_identity_status"] == "NOT_PROVABLE"


def test_running_days_never_inferred():
    event = project_usage_history_event(_installation(), REGISTRY)
    assert event["running_days"] is None


def test_seal_endpoint_excludes_unresolved_and_ambiguous_and_hold():
    installs = [
        _installation(installation_code="INSTL-101-2026", seal_type="T48MP", seal_size='2.1/8"'),  # A, confirmed
        _installation(installation_code="INSTL-102-2026", seal_type="T604", seal_size='3"'),  # C, unresolved
        _installation(installation_code="INSTL-103-2026", seal_type=None, seal_size=None),  # D
        _installation(
            installation_code="INSTL-104-2026", seal_type="T48MP", seal_size='2.1/8"',
            plant_equip_no="140-P-26B", pump_tag_number="140-P-26A",
        ),  # A but provenance hold
    ]
    events = list_seal_usage_history(installs, REGISTRY, "LTSA-SEAL-T48MP-2-1-8")
    assert [e["event_id"] for e in events] == ["INSTL-101-2026"]


def test_seal_endpoint_never_uses_pump_compatibility_as_usage():
    # Compatibility is not passed to this function at all -- there is no
    # parameter for it. This test documents/locks that contract: an
    # installation whose OWN type+size does not resolve to the seal must
    # never appear, no matter what pump it's on.
    installs = [_installation(seal_type="T604", seal_size='3"', plant_equip_no="945-P-9B")]
    events = list_seal_usage_history(installs, REGISTRY, "LTSA-SEAL-T48MP-2-1-8")
    assert events == []


def test_pump_endpoint_includes_unresolved_master_event():
    installs = [_installation(seal_type="T604", seal_size='3"', plant_equip_no="945-P-9B")]
    events = list_pump_seal_usage_history(installs, REGISTRY, "945-P-9B")
    assert len(events) == 1
    assert events[0]["master_association_status"] == "UNRESOLVED"


def test_pump_endpoint_matches_by_pump_tag_number_when_set_else_plant_equip_no():
    installs = [_installation(plant_equip_no="OLD-TAG", pump_tag_number="211-P-8A")]
    assert len(list_pump_seal_usage_history(installs, REGISTRY, "211-P-8A")) == 1
    assert len(list_pump_seal_usage_history(installs, REGISTRY, "OLD-TAG")) == 0


def test_empty_history_returns_empty_list_not_error():
    assert list_seal_usage_history([], REGISTRY, "LTSA-SEAL-T48MP-2-1-8") == []
    assert list_pump_seal_usage_history([], REGISTRY, "211-P-8A") == []


def test_stable_ordering_event_date_desc():
    installs = [
        _installation(installation_code="INSTL-A", report_date="2026-01-01"),
        _installation(installation_code="INSTL-B", report_date="2026-06-01"),
        _installation(installation_code="INSTL-C", report_date="2026-03-01"),
    ]
    events = list_pump_seal_usage_history(installs, REGISTRY, "211-P-8A")
    assert [e["event_id"] for e in events] == ["INSTL-B", "INSTL-C", "INSTL-A"]
