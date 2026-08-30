"""
MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017 -- semantic intent
routing tests. Tests assert on the DETECTED INTENT / routing decision,
never on one hardcoded final answer sentence -- proving "intent
recognition capable of understanding semantic variants", not
"if question == '<exact string>'".
"""

import sys
from pathlib import Path

import pytest

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.copilot_ask_service import (  # noqa: E402
    DATA_GAP,
    FACT,
    RECOMMENDATION,
    _detect_intent,
    _extract_seal_code,
    _handle_fleet_stock_status,
    ask_copilot,
)
from API.maintenance_intelligence_service import (  # noqa: E402
    flatten_stock_v1_fleet_rows,
    select_fleet_stock_by_predicate,
    select_latest_installation,
    select_most_frequent_leak_pump,
    select_stock_v1_pools_by_seal_code,
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


def test_mechanical_seal_installation_phrasing_routes_to_installation_intent():
    # MWO-LTSA-AI-COPILOT-NATURAL-LANGUAGE-ROUTING-017A Phase 4 acceptance #2.
    assert _detect_intent("pompa apa yang terakhir dipasang mechanical seal?") == "installation"


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
    assert _detect_intent("stock seal T48MP ada berapa?") == "inventory"
    assert _detect_intent("seal T48MP tersedia?") == "inventory"
    assert _detect_intent("stock mechanical seal T48MP") == "inventory"


def test_extract_seal_code_finds_a_real_code_not_a_time_word():
    assert _extract_seal_code("stok seal T48MP berapa?") == "T48MP"
    assert _extract_seal_code("berapa stock T6014DP?") == "T6014DP"
    assert _extract_seal_code("stock mechanical seal T48MP") == "T48MP"
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


def test_select_stock_v1_pools_by_seal_code_matches_by_exact_code():
    # Matches on seal_type, not seal_code -- seal_code is NULL on every
    # real production mechanical_seal_stock_pool row (verified before
    # writing this function); "T48MP" is the pool's own seal_type value.
    pools = [
        {"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5},
        {"stock_pool_id": "POOL-2", "seal_type": "SC-001", "quantity_available": 2},
    ]
    matches = select_stock_v1_pools_by_seal_code(pools, "T48MP")
    assert matches == ({"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5},)


def test_select_stock_v1_pools_by_seal_code_is_case_insensitive_but_never_substring():
    pools = [
        {"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5},
        {"stock_pool_id": "POOL-2", "seal_type": "T48LP", "quantity_available": 9},
    ]
    assert select_stock_v1_pools_by_seal_code(pools, "t48mp") == (pools[0],)
    assert select_stock_v1_pools_by_seal_code(pools, "T48") == ()


def test_select_stock_v1_pools_by_seal_code_returns_every_matching_pool_never_aggregated():
    # Mirrors real production data: three distinct T48MP pools exist,
    # each a different nominal_size -- genuinely separate stock, not
    # duplicates of one record.
    pools = [
        {"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5},
        {"stock_pool_id": "POOL-2", "seal_type": "T48MP", "quantity_available": 3},
    ]
    matches = select_stock_v1_pools_by_seal_code(pools, "T48MP")
    assert len(matches) == 2
    assert {p["stock_pool_id"] for p in matches} == {"POOL-1", "POOL-2"}


def test_select_stock_v1_pools_by_seal_code_unknown_code_returns_empty_tuple():
    assert select_stock_v1_pools_by_seal_code([{"seal_type": "T48MP"}], "UNKNOWN") == ()


# --- ask_copilot() end-to-end for the new fleet-wide intents -----------------------


class _FakeInstallationReportRepository:
    def __init__(self, records):
        self._records = records

    def list_installations(self):
        return {"success": True, "data": self._records}


class _FakeCMONGateway:
    def __init__(self, records):
        self._records = records

    def list_condition_monitoring_readings(self):
        return {"success": True, "data": self._records}


class _FakeMechanicalSealStockRepository:
    def __init__(self, pools):
        self._pools = pools

    def list_pools(self, **_kwargs):
        return {"success": True, "items": self._pools, "data": self._pools}


class _FakeConditionMonitoringReadingRepository:
    def __init__(self, readings_by_asset=None):
        self._readings_by_asset = readings_by_asset or {}

    def list_by_asset(self, asset_code):
        return list(self._readings_by_asset.get(asset_code, []))


class _FakeFleetExecutiveSummaryService:
    def __init__(self, summary=None, *, raises=False):
        self._summary = summary
        self._raises = raises
        self.build_calls = []

    def build(self, *, scope=None):
        self.build_calls.append(scope)
        if self._raises:
            raise RuntimeError("simulated fleet reliability service failure")
        return self._summary


class _FakePMOccurrenceRepository:
    def __init__(self, occurrences_by_asset=None):
        self._occurrences_by_asset = occurrences_by_asset or {}

    def list_by_asset(self, asset_code):
        return list(self._occurrences_by_asset.get(asset_code, []))


class _FakeCMReportRepository:
    def __init__(self, records=None, *, success=True):
        self._records = records if records is not None else []
        self._success = success

    def list_cm_reports(self, **_kwargs):
        return {"success": self._success, "data": self._records}


def _ask(
    question,
    *,
    installation_records=(),
    cmon_records=(),
    stock_pools=(),
    condition_monitoring_reading_repository=None,
    fleet_executive_summary_service=None,
    pm_occurrence_repository=None,
    cm_report_repository=None,
):
    return ask_copilot(
        question,
        None,
        None,
        pump_gateway=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway(list(cmon_records)),
        installation_report_repository=_FakeInstallationReportRepository(list(installation_records)),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository(list(stock_pools)),
        condition_monitoring_reading_repository=condition_monitoring_reading_repository
        or _FakeConditionMonitoringReadingRepository(),
        fleet_executive_summary_service=fleet_executive_summary_service or _FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=pm_occurrence_repository or _FakePMOccurrenceRepository(),
        cm_report_repository=cm_report_repository or _FakeCMReportRepository(),
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
    assert answer.evidence[0]["source"] == "InstallationReportRepository"


def test_primary_query_end_to_end_includes_seal_information_when_recorded():
    answer = _ask(
        "pompa apa yang terakhir dipasang mechanical seal?",
        installation_records=[
            {"plant_equip_no": "211-P-19A", "report_date": "2026-07-20", "installation_code": "I-2", "seal_code": "SC-002", "seal_type": "Cartridge"},
        ],
    )
    assert answer.kind == FACT
    assert "SC-002" in answer.answer
    assert "Cartridge" in answer.answer


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


def test_stock_query_end_to_end_reads_stock_v1_quantity_available():
    answer = _ask(
        "stok seal T48MP berapa?",
        stock_pools=[{"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 12, "stock_location": "Warehouse A"}],
    )
    assert answer.kind == FACT
    assert "T48MP" in answer.answer
    assert "12" in answer.answer
    assert answer.evidence[0]["source"] == "MechanicalSealStockV1"


def test_stock_query_without_seal_keyword_still_extracts_code():
    # PHASE 4 acceptance #5: "berapa stock T6014DP?" -- no "seal" word at all.
    answer = _ask(
        "stock T6014DP ada berapa?",
        stock_pools=[{"stock_pool_id": "POOL-9", "seal_type": "T6014DP", "quantity_available": 7}],
    )
    assert answer.kind == FACT
    assert "T6014DP" in answer.answer
    assert "7" in answer.answer


def test_stock_query_null_quantity_reports_unknown_not_zero():
    answer = _ask(
        "stock seal T48MP ada berapa?",
        stock_pools=[{"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": None}],
    )
    assert answer.kind == FACT
    assert "unknown" in answer.answer.lower()
    assert "0" not in answer.answer


def test_stock_query_zero_quantity_reports_out_of_stock():
    answer = _ask(
        "stock seal T48MP ada berapa?",
        stock_pools=[{"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0}],
    )
    assert answer.kind == FACT
    assert "out of stock" in answer.answer.lower()


def test_stock_query_multiple_pools_reported_separately_never_summed():
    answer = _ask(
        "stock seal T48MP ada berapa?",
        stock_pools=[
            {"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5, "stock_location": "Warehouse A"},
            {"stock_pool_id": "POOL-2", "seal_type": "T48MP", "quantity_available": 3, "stock_location": "Warehouse B"},
        ],
    )
    assert answer.kind == FACT
    assert "POOL-1" in answer.answer and "POOL-2" in answer.answer
    assert "5 unit" in answer.answer and "3 unit" in answer.answer  # each pool's own real quantity, never summed
    assert len(answer.evidence) == 2


def test_stock_query_unknown_seal_code_is_truthful_data_gap():
    answer = _ask("stock seal UNKNOWNCODE1 ada berapa?", stock_pools=[{"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5}])
    assert answer.kind == DATA_GAP
    assert "UNKNOWNCODE1" in answer.answer


def test_ask_copilot_no_longer_accepts_legacy_seal_stock_gateway_kwarg():
    # Structural proof that legacy seal_stock cannot affect any answer:
    # the parameter itself no longer exists on ask_copilot()'s signature.
    import inspect

    from API.copilot_ask_service import ask_copilot as _ask_copilot_fn

    assert "seal_stock_gateway" not in inspect.signature(_ask_copilot_fn).parameters
    assert "mechanical_seal_stock_repository" in inspect.signature(_ask_copilot_fn).parameters


def test_unsupported_topic_still_returns_couldnt_match_message():
    answer = _ask("siapa presiden pertama indonesia?")
    assert answer.kind == DATA_GAP
    assert "couldn't match" in answer.answer.lower()


def test_tag_scoped_condition_monitoring_returns_latest_reading():
    # MWO: CLOSE FINAL LTSA AI WHATSAPP QUERY GAPS -- Phase 1. Tag-scoped
    # condition_monitoring now has a real per-asset tool
    # (condition_monitoring_reading_repository.list_by_asset, already
    # ordered newest-first by the repository's own query), closing the
    # gap the prior MWO's KeyError-safety fix only made non-crashing.
    assert _detect_intent("apakah ada kebocoran di CMON 211-P-13AR?") == "condition_monitoring"
    repo = _FakeConditionMonitoringReadingRepository({
        "211-P-13AR": [
            {
                "condition_monitoring_reading_code": "CMONR-NEWEST",
                "reading_date": "2026-08-30",
                "finding": "Kebocoran mechanical seal",
                "workflow_status": "SUBMITTED",
                "technical_recommendation": None,
                "source_reference": "WHATSAPP::wa-1",
            },
        ]
    })
    # _ask() hardcodes tag=None (fleet-wide only); call ask_copilot()
    # directly for this tag-scoped case.
    answer = ask_copilot(
        "apakah ada kebocoran di CMON 211-P-13AR?",
        "211-P-13AR",
        None,
        pump_gateway=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=repo,
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
        language="id",
    )
    assert answer.kind == FACT
    assert "CMON terakhir: 2026-08-30" in answer.answer
    assert "Temuan: Kebocoran mechanical seal" in answer.answer
    assert "Status: SUBMITTED" in answer.answer
    assert "Rekomendasi:" not in answer.answer  # None -- never invented
    assert "Sumber: WHATSAPP::wa-1" in answer.answer
    assert answer.evidence == (
        {"source": "ConditionMonitoringReadingRepository", "reference": "CMONR-NEWEST", "field": "finding", "value": "Kebocoran mechanical seal"},
    )


def test_tag_scoped_condition_monitoring_multiple_records_newest_selected():
    repo = _FakeConditionMonitoringReadingRepository({
        "211-P-13AR": [
            {"condition_monitoring_reading_code": "CMONR-NEWEST", "reading_date": "2026-08-30", "finding": "Newest finding"},
            {"condition_monitoring_reading_code": "CMONR-OLDER", "reading_date": "2026-01-01", "finding": "Older finding"},
        ]
    })
    answer = ask_copilot(
        "CMON terakhir 211-P-13AR apa?", "211-P-13AR", None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=repo,
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
    )
    assert "Newest finding" in answer.answer
    assert "Older finding" not in answer.answer


def test_tag_scoped_condition_monitoring_no_data_is_truthful_fact_not_fabricated():
    repo = _FakeConditionMonitoringReadingRepository({})
    answer = ask_copilot(
        "CMON terakhir 211-P-13AR apa?", "211-P-13AR", None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=repo,
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
        language="id",
    )
    assert answer.answer == "Belum ada data Condition Monitoring untuk 211-P-13AR."
    assert answer.kind == FACT
    assert answer.evidence == ()


def test_tag_scoped_condition_monitoring_missing_fields_never_invented():
    repo = _FakeConditionMonitoringReadingRepository({
        "211-P-13AR": [{"condition_monitoring_reading_code": "CMONR-BARE"}],
    })
    answer = ask_copilot(
        "CMON terakhir 211-P-13AR apa?", "211-P-13AR", None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=repo,
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
        language="id",
    )
    assert "CMON terakhir: tidak diketahui" in answer.answer
    assert "Temuan: tidak ada catatan" in answer.answer
    assert "Status:" not in answer.answer
    assert "Rekomendasi:" not in answer.answer
    assert "Sumber:" not in answer.answer


def test_tag_scoped_condition_monitoring_repository_failure_is_data_gap_not_a_crash():
    class _RaisingRepository:
        def list_by_asset(self, asset_code):
            raise RuntimeError("simulated DB failure")

    answer = ask_copilot(
        "CMON terakhir 211-P-13AR apa?", "211-P-13AR", None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=_RaisingRepository(),
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
    )
    assert answer.kind == DATA_GAP
    assert answer.evidence == ()


def test_tag_scoped_intent_with_no_registered_handler_is_graceful_data_gap_not_a_crash(monkeypatch):
    # Generic regression for the fix behind TOOL_HANDLERS.get(intent):
    # any FUTURE intent _detect_intent recognizes without a matching
    # TOOL_HANDLERS entry must degrade to DATA_GAP, never KeyError --
    # proven here without depending on condition_monitoring specifically,
    # since that intent now has a real handler.
    import API.copilot_ask_service as copilot_ask_service_module

    monkeypatch.delitem(copilot_ask_service_module.TOOL_HANDLERS, "pump_history")
    answer = ask_copilot(
        "riwayat pompa 211-P-13AR", "211-P-13AR", None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FakeCMONGateway([]),
        installation_report_repository=_FakeInstallationReportRepository([]),
        mechanical_seal_stock_repository=_FakeMechanicalSealStockRepository([]),
        condition_monitoring_reading_repository=_FakeConditionMonitoringReadingRepository(),
        fleet_executive_summary_service=_FakeFleetExecutiveSummaryService(),
        pm_occurrence_repository=_FakePMOccurrenceRepository(),
        cm_report_repository=_FakeCMReportRepository(),
    )
    assert answer.kind == DATA_GAP


# --- MWO-LTSA-AI-COPILOT-FLEET-STOCK-V1-017B: fleet-wide stock status -------------

_POOL_OUT = {"stock_pool_id": "POOL-OUT", "seal_type": "T48MP", "quantity_available": 0, "applications": [{"equipment_tag": "211-P-01A"}]}
_POOL_UNKNOWN = {"stock_pool_id": "POOL-UNK", "seal_type": "T6014DP", "quantity_available": None, "applications": [{"equipment_tag": "211-P-02A"}]}
_POOL_AVAILABLE = {"stock_pool_id": "POOL-OK", "seal_type": "SC-001", "quantity_available": 5, "applications": [{"equipment_tag": "211-P-03A"}]}
_ALL_POOLS = (_POOL_OUT, _POOL_UNKNOWN, _POOL_AVAILABLE)


# A. Indonesian fleet no-stock query routes without tag.
def test_indonesian_fleet_out_of_stock_query_routes_without_tag():
    assert _detect_intent("seal pompa mana yang ga ada stocknya?") == "inventory"
    assert _extract_seal_code("seal pompa mana yang ga ada stocknya?") is None
    answer = _ask("seal pompa mana yang ga ada stocknya?", stock_pools=_ALL_POOLS)
    assert answer.kind == FACT
    assert "211-P-01A" in answer.answer
    assert "211-P-02A" not in answer.answer
    assert "211-P-03A" not in answer.answer


# B. English fleet no-stock query routes without tag.
def test_english_fleet_out_of_stock_query_routes_without_tag():
    for question in ("which pumps have no seal stock?", "show pumps with zero seal inventory"):
        assert _detect_intent(question) == "inventory", question
        answer = _ask(question, stock_pools=_ALL_POOLS)
        assert answer.kind == FACT
        assert "211-P-01A" in answer.answer


# C. quantity=0 classified OUT_OF_STOCK.
def test_zero_quantity_classified_out_of_stock():
    rows = select_fleet_stock_by_predicate(flatten_stock_v1_fleet_rows(_ALL_POOLS), "OUT_OF_STOCK")
    assert [r["equipment_tag"] for r in rows] == ["211-P-01A"]


# D. quantity=NULL classified UNKNOWN_STOCK.
def test_null_quantity_classified_unknown_stock():
    rows = select_fleet_stock_by_predicate(flatten_stock_v1_fleet_rows(_ALL_POOLS), "UNKNOWN_STOCK")
    assert [r["equipment_tag"] for r in rows] == ["211-P-02A"]


# E. NULL never reported as zero.
def test_null_quantity_never_reported_as_zero():
    answer = _ask("pompa mana yang stock sealnya unknown?", stock_pools=_ALL_POOLS)
    assert answer.kind == FACT
    assert "211-P-02A" in answer.answer
    assert "211-P-02A — T6014DP — unknown" in answer.answer
    assert "211-P-02A — T6014DP — 0" not in answer.answer


def test_out_of_stock_predicate_variants_and_more_examples():
    for question in (
        "pompa apa yang sealnya out of stock?",
        "mana yang stok sealnya kosong?",
        "berapa pompa yang sealnya tidak tersedia?",
    ):
        answer = _ask(question, stock_pools=_ALL_POOLS)
        assert answer.kind == FACT, question
        assert "211-P-01A" in answer.answer, question


def test_lowest_stock_predicate():
    pools = (
        {"stock_pool_id": "P1", "seal_type": "T48MP", "quantity_available": 5, "applications": [{"equipment_tag": "TAG-A"}]},
        {"stock_pool_id": "P2", "seal_type": "T48MP", "quantity_available": 1, "applications": [{"equipment_tag": "TAG-B"}]},
    )
    answer = _ask("seal apa yang stoknya paling sedikit?", stock_pools=pools)
    assert answer.kind == FACT
    assert "TAG-B" in answer.answer
    assert "TAG-A" not in answer.answer


# F. tag-specific Stock V1 query from 017A still works.
def test_tag_specific_017a_stock_query_still_works():
    answer = _ask(
        "stock seal T48MP ada berapa?",
        stock_pools=[{"stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 12, "stock_location": "Warehouse A"}],
    )
    assert answer.kind == FACT
    assert "T48MP" in answer.answer
    assert answer.evidence[0]["source"] == "MechanicalSealStockV1"


# G. multi-pool behavior remains truthful (never aggregated).
def test_multi_pool_fleet_rows_never_aggregated_across_pools():
    pools = (
        {"stock_pool_id": "P1", "seal_type": "T48MP", "quantity_available": 0, "applications": [{"equipment_tag": "TAG-A"}]},
        {"stock_pool_id": "P2", "seal_type": "T48MP", "quantity_available": 3, "applications": [{"equipment_tag": "TAG-A"}]},
    )
    # Same pump, two distinct real pool applications -- both rows must
    # survive independently; TAG-A must appear in OUT_OF_STOCK (pool P1)
    # without inheriting pool P2's positive quantity.
    out_of_stock = select_fleet_stock_by_predicate(flatten_stock_v1_fleet_rows(pools), "OUT_OF_STOCK")
    assert len(out_of_stock) == 1
    assert out_of_stock[0]["stock_pool_id"] == "P1"


# H. no legacy seal_stock authority.
def test_fleet_stock_handler_has_no_legacy_seal_stock_parameter():
    import inspect

    assert "seal_stock_gateway" not in inspect.signature(_handle_fleet_stock_status).parameters


# I. unsupported question still fails honestly.
def test_fleet_stock_no_matches_is_truthful_data_gap():
    answer = _ask("pompa mana yang stock sealnya unknown?", stock_pools=[_POOL_OUT, _POOL_AVAILABLE])
    assert answer.kind == DATA_GAP
    assert "No pumps found" in answer.answer


def test_fleet_stock_data_unavailable_is_data_gap_not_fabricated():
    class _FailingRepo:
        def list_pools(self, **_kwargs):
            return {"success": False}

    answer = ask_copilot(
        "seal pompa mana yang ga ada stocknya?", None, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=_FailingRepo(),
        condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None,
        cm_report_repository=None,
    )
    assert answer.kind == DATA_GAP
    assert "unavailable" in answer.answer.lower()


# --- MWO: CLOSE FINAL LTSA AI WHATSAPP QUERY GAPS -- Phase 2: fleet priority ------
#
# _handle_fleet_priority reuses FleetExecutiveSummaryService.build(scope=...)
# unchanged -- the exact same canonical ranking routers/fleet.py's own
# /api/ltsa/fleet/powerbi endpoint already serves. No new scoring formula.


def _fleet_priority_query(fleet_executive_summary_service, scope=None):
    return ask_copilot(
        "pompa mana yang perlu perhatian hari ini?", None, scope,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=fleet_executive_summary_service,
        pm_occurrence_repository=None,
        cm_report_repository=None,
    )


class _FakeTopRisk:
    def __init__(self, tag_number, title, priority, action, description="test evidence"):
        self.tag_number = tag_number
        self.title = title
        self.priority = priority
        self.action = action
        self.description = description


class _FakeFleetExecutiveSummary:
    def __init__(self, *, fleet_status="ATTENTION", top_risks=()):
        self.fleet_status = fleet_status
        self.top_risks = top_risks


@pytest.mark.parametrize(
    "question",
    [
        "Pompa mana yang perlu perhatian hari ini?",
        "Pompa paling kritis apa?",
        "Ada equipment yang perlu diperhatikan?",
        "Prioritas pompa hari ini",
        "Pompa paling kritis di area saya?",
    ],
)
def test_fleet_priority_wording_variants_all_route_to_fleet_priority_intent(question):
    assert _detect_intent(question) == "fleet_priority"


def test_fleet_priority_query_reuses_canonical_top_risks():
    summary = _FakeFleetExecutiveSummary(
        top_risks=(_FakeTopRisk("211-P-13AR", "Vibration trending high", 120, "Schedule CM inspection"),)
    )
    service = _FakeFleetExecutiveSummaryService(summary)
    answer = _fleet_priority_query(service)
    assert answer.kind == RECOMMENDATION
    assert "211-P-13AR" in answer.answer
    assert "Vibration trending high" in answer.answer
    assert "Schedule CM inspection" in answer.answer
    # MWO-LTSA-FLEET-ATTENTION-001 -- rewritten to the mission's concise
    # operational format (numbered pump list + Source footer); fleet_status
    # is no longer rendered inline in this answer.
    assert "Source: LTSA canonical data" in answer.answer
    assert answer.evidence == (
        {"source": "FleetExecutiveSummaryService", "reference": "211-P-13AR", "field": "priority", "value": "120"},
    )


def test_fleet_priority_ranking_never_recomputed_only_passed_through():
    # Proves no new scoring formula: the handler never sorts/filters
    # top_risks itself -- whatever order/content the canonical service
    # returns is what gets reported, verbatim.
    summary = _FakeFleetExecutiveSummary(
        top_risks=(
            _FakeTopRisk("211-P-13AR", "Low priority risk", 10, "Monitor"),
            _FakeTopRisk("210-P-05AR", "High priority risk", 200, "Escalate"),
        )
    )
    service = _FakeFleetExecutiveSummaryService(summary)
    answer = _fleet_priority_query(service)
    assert answer.answer.index("211-P-13AR") < answer.answer.index("210-P-05AR")


def test_fleet_priority_authorization_scope_passed_into_canonical_build():
    # The canonical query itself operates on authorized scope (never a
    # global ranking filtered/hidden after the fact) -- proven by
    # asserting the exact scope this handler received is the exact scope
    # forwarded into build(), not re-derived or dropped.
    summary = _FakeFleetExecutiveSummary(top_risks=())
    service = _FakeFleetExecutiveSummaryService(summary)
    scope = frozenset({"HSC", "S_PAKNING", "HCC"})
    _fleet_priority_query(service, scope=scope)
    assert service.build_calls == [scope]


def test_fleet_priority_no_actionable_assets_is_truthful_fact():
    summary = _FakeFleetExecutiveSummary(fleet_status="NORMAL", top_risks=())
    answer = _fleet_priority_query(_FakeFleetExecutiveSummaryService(summary))
    assert answer.kind == FACT
    assert "no pumps" in answer.answer.lower()


def test_fleet_priority_empty_fleet_is_truthful_fact_not_a_crash():
    summary = _FakeFleetExecutiveSummary(fleet_status="UNKNOWN", top_risks=())
    answer = _fleet_priority_query(_FakeFleetExecutiveSummaryService(summary))
    assert answer.kind == FACT
    assert answer.evidence == ()


def test_fleet_priority_service_failure_is_data_gap_not_a_crash():
    answer = _fleet_priority_query(_FakeFleetExecutiveSummaryService(None, raises=True))
    assert answer.kind == DATA_GAP
    assert answer.evidence == ()


def test_fleet_priority_malformed_service_result_never_crashes():
    class _MalformedSummary:
        fleet_status = "ATTENTION"
        top_risks = None  # malformed: not a tuple

    answer = _fleet_priority_query(_FakeFleetExecutiveSummaryService(_MalformedSummary()))
    assert answer.kind == FACT
    assert "no pumps" in answer.answer.lower()


def test_fleet_priority_query_path_never_calls_any_write_method():
    # Read-only by construction: _FakeFleetExecutiveSummaryService exposes
    # only build() -- if the handler ever called anything else, this
    # test's own AttributeError would fail it.
    summary = _FakeFleetExecutiveSummary(top_risks=())
    service = _FakeFleetExecutiveSummaryService(summary)
    _fleet_priority_query(service)
    assert service.build_calls == [None]
