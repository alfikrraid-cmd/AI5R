"""
MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- semantic intent
routing tests. Tests assert on the DETECTED INTENT / routing decision,
never on one hardcoded final answer sentence -- proving "intent
recognition capable of understanding semantic variants", not
"if question == '<exact string>'".
"""

import sys
from pathlib import Path

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.copilot_ask_service import (  # noqa: E402
    DATA_GAP,
    FACT,
    _detect_intent,
    _extract_seal_code,
    ask_copilot,
)
from API.maintenance_intelligence_service import (  # noqa: E402
    select_latest_installation,
    select_most_frequent_leak_pump,
    select_seal_stock,
)


# --- Indonesian variants -----------------------------------------------------


def test_indonesian_installation_variants_all_route_to_installation_intent():
    variants = [
        "pompa mana yang terakhir di pasang?",
        "pompa mana yang terakhir dipasang?",
        "pompa terakhir yang dipasang apa?",
        "apa equipment yang terakhir dipasang?",
        "terakhir pasang seal di pompa mana?",
        "installation terakhir pump apa?",
    ]
    for question in variants:
        assert _detect_intent(question) == "installation", question


# --- English variants -----------------------------------------------------------


def test_english_installation_variants_all_route_to_installation_intent():
    variants = ["latest pump installation", "which pump was installed last?"]
    for question in variants:
        assert _detect_intent(question) == "installation", question


# --- seal replacement (installation domain, not current_seal) -------------------


def test_seal_replacement_wording_routes_to_installation_not_current_seal():
    assert _detect_intent("kapan seal terakhir diganti?") == "installation"


def test_current_seal_wording_without_replacement_still_routes_to_current_seal():
    # Regression: the pre-existing current_seal intent must not be broken
    # by the new installation-replacement guard.
    assert _detect_intent("seal terakhir apa?") == "current_seal"
    assert _detect_intent("what's the current seal?") == "current_seal"


# --- PM / condition monitoring / CM distinction ------------------------------------


def test_pm_terakhir_with_embedded_tag_routes_to_pm_intent():
    assert _detect_intent("PM terakhir 211-P-19A") == "pm"


def test_pm_terakhir_without_tag_routes_to_pm_intent():
    assert _detect_intent("kapan PM terakhir?") == "pm"


def test_leak_wording_routes_to_condition_monitoring_never_cm():
    assert _detect_intent("pompa mana yang paling sering bocor?") == "condition_monitoring"
    assert _detect_intent("which pump leaks most often?") == "condition_monitoring"


def test_breakdown_wording_still_routes_to_cm_not_condition_monitoring():
    # Regression: "Do not confuse Condition Monitoring with Corrective
    # Maintenance" -- kerusakan/breakdown must stay on the CM path.
    assert _detect_intent("pompa mana yang paling sering rusak?") == "cm"


# --- stock ------------------------------------------------------------------------


def test_stock_question_with_seal_code_routes_to_inventory_not_seal_compat():
    assert _detect_intent("stok seal T48MP berapa?") == "inventory"


def test_extract_seal_code_finds_a_real_code_not_a_time_word():
    assert _extract_seal_code("stok seal T48MP berapa?") == "T48MP"
    assert _extract_seal_code("kapan seal terakhir diganti?") is None


# --- negative: genuinely unsupported topic -----------------------------------------


def test_genuinely_unrelated_question_returns_none_intent():
    assert _detect_intent("siapa presiden pertama indonesia?") is None


# --- pure selection functions (maintenance_intelligence_service) ------------------


def test_select_latest_installation_picks_the_max_recorded_date():
    records = [
        {"plant_equip_no": "P-1", "report_date": "2026-01-01", "installation_code": "I-1"},
        {"plant_equip_no": "P-2", "report_date": "2026-06-15", "installation_code": "I-2"},
        {"plant_equip_no": "P-3", "report_date": "2026-03-01", "installation_code": "I-3"},
    ]
    latest = select_latest_installation(records)
    assert latest["plant_equip_no"] == "P-2"


def test_select_latest_installation_ignores_records_with_no_parseable_date():
    records = [
        {"plant_equip_no": "P-1", "report_date": None, "installation_code": "I-1"},
        {"plant_equip_no": "P-2", "report_date": "not-a-date", "installation_code": "I-2"},
    ]
    assert select_latest_installation(records) is None


def test_select_latest_installation_empty_list_returns_none():
    assert select_latest_installation([]) is None


def test_select_most_frequent_leak_pump_counts_flagged_readings_only():
    readings = [
        {"asset_code": "P-1", "mechanical_seal_leak_de": True},
        {"asset_code": "P-1", "mechanical_seal_leak_nde": True},
        {"asset_code": "P-2", "mechanical_seal_leak_de": True},
        {"asset_code": "P-3", "mechanical_seal_leak_de": False},
    ]
    assert select_most_frequent_leak_pump(readings) == ("P-1", 2)


def test_select_most_frequent_leak_pump_no_leaks_returns_none():
    assert select_most_frequent_leak_pump([{"asset_code": "P-1", "mechanical_seal_leak_de": False}]) is None


def test_select_seal_stock_matches_by_exact_code():
    records = [{"seal_code": "T48MP", "quantity_on_hand": 5}, {"seal_code": "SC-001", "quantity_on_hand": 2}]
    assert select_seal_stock(records, "T48MP")["quantity_on_hand"] == 5
    assert select_seal_stock(records, "UNKNOWN") is None


# --- ask_copilot() end-to-end for the new fleet-wide intents -----------------------


class _FakeInstallationGateway:
    def __init__(self, records):
        self._records = records

    def list_installations(self):
        return {"success": True, "data": self._records}


class _FakeCMONGateway:
    def __init__(self, records):
        self._records = records

    def list_condition_monitoring_readings(self):
        return {"success": True, "data": self._records}


class _FakeSealStockGateway:
    def __init__(self, records):
        self._records = records

    def list_seal_stocks(self):
        return {"success": True, "data": self._records}


def _ask(question, *, installation_records=(), cmon_records=(), stock_records=()):
    return ask_copilot(
        question,
        None,
        None,
        pump_gateway=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=_FakeInstallationGateway(list(installation_records)),
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        seal_stock_gateway=_FakeSealStockGateway(list(stock_records)),
        condition_monitoring_reading_gateway=_FakeCMONGateway(list(cmon_records)),
    )


def test_primary_query_end_to_end_returns_the_latest_installed_pump():
    answer = _ask(
        "pompa mana yang terakhir di pasang?",
        installation_records=[
            {"plant_equip_no": "211-P-13AR", "report_date": "2026-01-01", "installation_code": "I-1", "seal_code": "SC-001"},
            {"plant_equip_no": "211-P-19A", "report_date": "2026-07-20", "installation_code": "I-2", "seal_code": "SC-002"},
        ],
    )
    assert answer.kind == FACT
    assert "211-P-19A" in answer.answer
    assert "2026-07-20" in answer.answer
    assert answer.evidence[0]["source"] == "InstallationGateway"


def test_primary_query_with_no_installation_records_is_truthful_data_gap_not_unsupported():
    answer = _ask("pompa mana yang terakhir dipasang?", installation_records=[])
    assert answer.kind == DATA_GAP
    assert "couldn't match" not in answer.answer.lower()
    assert "installation history is absent" in answer.answer.lower()


def test_leak_frequency_query_end_to_end():
    answer = _ask(
        "pompa mana yang paling sering bocor?",
        cmon_records=[
            {"asset_code": "211-P-13AR", "mechanical_seal_leak_de": True},
            {"asset_code": "211-P-13AR", "mechanical_seal_leak_de": True},
            {"asset_code": "211-P-19A", "mechanical_seal_leak_nde": True},
        ],
    )
    assert answer.kind == FACT
    assert "211-P-13AR" in answer.answer
    assert "2" in answer.answer


def test_stock_query_end_to_end():
    answer = _ask("stok seal T48MP berapa?", stock_records=[{"seal_code": "T48MP", "quantity_on_hand": 12, "location": "Warehouse A"}])
    assert answer.kind == FACT
    assert "T48MP" in answer.answer
    assert "12" in answer.answer


def test_unsupported_topic_still_returns_couldnt_match_message():
    answer = _ask("siapa presiden pertama indonesia?")
    assert answer.kind == DATA_GAP
    assert "couldn't match" in answer.answer.lower()
