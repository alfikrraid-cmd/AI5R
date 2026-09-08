"""
MWO-LTSA-ASSET-DIRECTORY-001 -- LTSA Asset Directory / Fleet Discovery test suite.
Covers all 39 requirements:
1-9: Intent routing for discovery queries
10-19: Canonical domain model & MA resolution
20-24: Scoped authorization bounds (fail-closed)
25-27: Seal semantics (current_seal vs compat vs stock)
28-35: Regressions against existing intents and tag normalization
36-39: Output formatting (Indonesian card, S. PAKNING display, truncation, scoped counts)
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.copilot_ask_service import (
    DATA_GAP,
    FACT,
    _detect_intent,
    _extract_pump_tags,
    _normalize_pump_tag,
    ask_copilot,
)
from API.pump_area_scope import (
    MA_AREA_GROUPS,
    format_area_display,
    is_area_in_scope,
    normalize_area_token,
    resolve_area_ma,
    resolve_ma_areas,
)


# ==============================================================================
# FAKES & TEST FIXTURES
# ==============================================================================

class FakePumpGateway:
    def __init__(self, pumps: list[dict[str, Any]] | None = None):
        self.pumps = pumps or []

    def get_pump(self, tag_number: str) -> dict[str, Any]:
        for p in self.pumps:
            if p.get("tag_number") == tag_number:
                return {"success": True, "data": p}
        return {"success": False, "data": None}

    def list_pumps(self) -> dict[str, Any]:
        return {"success": True, "data": list(self.pumps)}


@dataclass
class FakeCurrentSeal:
    seal_code: str | None = None
    seal_name: str | None = None
    installed_at: str | None = None
    source: str = "InstallationRecord"
    installation_code: str | None = "I-001"


class FakeEquipmentTimelineService:
    def __init__(self, seals_by_tag: dict[str, FakeCurrentSeal | None] | None = None):
        self.seals_by_tag = seals_by_tag or {}

    def build_current_seal(self, tag: str) -> FakeCurrentSeal | None:
        return self.seals_by_tag.get(tag)


class FakeStockRepository:
    def __init__(self, pools: list[dict[str, Any]] | None = None):
        self.pools = pools or []

    def list_pools(self, **_kwargs) -> dict[str, Any]:
        return {"success": True, "data": self.pools}


# Sample fleet for tests
TEST_PUMPS = [
    {"tag_number": "211-P-10A", "area": "HSC", "status": "ACTIVE"},
    {"tag_number": "211-P-10B", "area": "HSC", "status": "ACTIVE"},
    {"tag_number": "212-P-01A", "area": "S_PAKNING", "status": "ACTIVE"},
    {"tag_number": "213-P-05A", "area": "HCC", "status": "ACTIVE"},
    {"tag_number": "213-P-05B", "area": "HCC", "status": "ACTIVE"},
    {"tag_number": "110-P-12A", "area": "HOC", "status": "ACTIVE"},
    {"tag_number": "110-P-12B", "area": "HOC", "status": "ACTIVE"},
    {"tag_number": "310-P-01A", "area": "UTL", "status": "ACTIVE"},
    {"tag_number": "410-P-02A", "area": "OM", "status": "ACTIVE"},
]

TEST_STOCK_POOLS = [
    {
        "stock_pool_id": "POOL-1",
        "seal_type": "T48LP",
        "quantity_available": 2,
        "applications": [{"equipment_tag": "211-P-10A"}],
    }
]

TEST_SEALS = {
    "211-P-10A": FakeCurrentSeal(seal_code="T48LP", seal_name="Cartridge", installed_at="2025-01-15"),
    "110-P-12B": FakeCurrentSeal(seal_code="SC-001", seal_name="Single", installed_at="2024-11-20"),
    # 211-P-10B has NO confirmed current seal
}


def _ask_helper(
    question: str,
    *,
    tag: str | None = None,
    scope: frozenset[str] | None = None,
    pumps: list[dict[str, Any]] | None = None,
    seals: dict[str, FakeCurrentSeal | None] | None = None,
    pools: list[dict[str, Any]] | None = None,
    language: str = "id",
):
    pump_gw = FakePumpGateway(pumps if pumps is not None else TEST_PUMPS)
    timeline_svc = FakeEquipmentTimelineService(seals if seals is not None else TEST_SEALS)
    stock_repo = FakeStockRepository(pools if pools is not None else TEST_STOCK_POOLS)

    return ask_copilot(
        question,
        tag,
        scope,
        pump_gateway=pump_gw,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=timeline_svc,
        condition_monitoring_reading_gateway=None,
        installation_report_repository=None,
        mechanical_seal_stock_repository=stock_repo,
        condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None,
        cm_report_repository=None,
        language=language,
    )


# ==============================================================================
# 1-9: INTENT ROUTING
# ==============================================================================

def test_intent_01_list_pompa_di_ma2():
    assert _detect_intent("list pompa di ma2") == "asset_directory"


def test_intent_02_pompa_hsc():
    assert _detect_intent("pompa hsc") == "asset_directory"


def test_intent_03_list_pompa_hoc():
    assert _detect_intent("list pompa hoc") == "asset_directory"


def test_intent_04_211_p_10a_area_mana():
    assert _detect_intent("211-P-10A area mana") == "asset_directory"
    assert _detect_intent("area mana", tag="211-P-10A") == "asset_directory"


def test_intent_05_211p10a_masuk_ma_berapa():
    assert _detect_intent("211p10a masuk MA berapa") == "asset_directory"
    assert _detect_intent("masuk MA berapa", tag="211-P-10A") == "asset_directory"


def test_intent_06_110_p_12b_hoc_atau_hsc():
    assert _detect_intent("110-P-12B HOC atau HSC") == "asset_directory"
    assert _detect_intent("HOC atau HSC", tag="110-P-12B") == "asset_directory"


def test_intent_07_berapa_pompa_di_hcc():
    assert _detect_intent("berapa pompa di HCC") == "asset_directory"


def test_intent_08_list_pompa_ma2_hsc():
    assert _detect_intent("list pompa MA2 HSC") == "asset_directory"


def test_intent_09_pompa_area_utl():
    assert _detect_intent("pompa area UTL") == "asset_directory"


# ==============================================================================
# 10-19: DOMAIN MODEL & CANONICAL RESOLVERS
# ==============================================================================

def test_domain_10_ma1_maps_to_hoc():
    assert resolve_ma_areas("MA1") == frozenset({"HOC"})


def test_domain_11_ma2_maps_to_hsc_s_pakning_hcc():
    assert resolve_ma_areas("MA2") == frozenset({"HSC", "S_PAKNING", "HCC"})


def test_domain_12_ma3_maps_to_utl():
    assert resolve_ma_areas("MA3") == frozenset({"UTL"})


def test_domain_13_ma4_maps_to_om():
    assert resolve_ma_areas("MA4") == frozenset({"OM"})


def test_domain_14_hsc_resolves_to_ma2():
    assert resolve_area_ma("HSC") == "MA2"


def test_domain_15_hcc_resolves_to_ma2():
    assert resolve_area_ma("HCC") == "MA2"


def test_domain_16_s_pakning_resolves_to_ma2():
    assert resolve_area_ma("S_PAKNING") == "MA2"


def test_domain_17_unknown_area_resolves_to_none():
    assert resolve_area_ma("UNKNOWN") is None
    assert resolve_area_ma(None) is None


def test_domain_18_invalid_ma_handled_safely():
    assert resolve_ma_areas("MA5") is None
    assert resolve_ma_areas(None) is None
    answer = _ask_helper("list pompa di ma5")
    assert answer.kind == DATA_GAP
    assert "tidak dikenali" in answer.answer


def test_domain_19_ma_area_intersection_correct():
    # MA2 + HSC -> valid intersection
    ans_valid = _ask_helper("list pompa MA2 HSC")
    assert ans_valid.kind == FACT
    assert "Pompa MA2 HSC — 2" in ans_valid.answer
    assert "211-P-10A" in ans_valid.answer
    assert "213-P-05A" not in ans_valid.answer  # HCC excluded

    # MA1 + HSC -> invalid intersection
    ans_invalid = _ask_helper("list pompa MA1 HSC")
    assert ans_invalid.kind == DATA_GAP
    assert "bukan bagian dari MA1" in ans_invalid.answer


# ==============================================================================
# 20-24: AUTHORIZATION & SCOPE BOUNDS (FAIL-CLOSED)
# ==============================================================================

def test_auth_20_restricted_user_cannot_list_out_of_scope_pumps():
    # User restricted to HSC only
    answer = _ask_helper("list pompa di ma2", scope=frozenset({"HSC"}))
    assert answer.kind == FACT
    assert "211-P-10A" in answer.answer
    assert "211-P-10B" in answer.answer
    # Must NOT disclose S_PAKNING or HCC pumps
    assert "212-P-01A" not in answer.answer
    assert "213-P-05A" not in answer.answer
    assert "HCC" not in answer.answer
    assert "S. PAKNING" not in answer.answer


def test_auth_21_restricted_user_cannot_count_out_of_scope_pumps():
    # User restricted to HSC asks for HCC count
    answer = _ask_helper("berapa pompa di HCC", scope=frozenset({"HSC"}))
    assert answer.kind == FACT
    assert "Terdapat 0 pompa di HCC." in answer.answer


def test_auth_22_restricted_user_cannot_find_out_of_scope_pump():
    # 110-P-12B is in HOC. User restricted to HSC.
    answer = _ask_helper("110-P-12B area mana", scope=frozenset({"HSC"}))
    assert answer.kind == DATA_GAP
    assert answer.answer == "Tag pompa 110-P-12B tidak ditemukan."
    # Never leak existence or area
    assert "HOC" not in answer.answer


def test_auth_23_group_allowed_scope_cannot_widen_sender_scope():
    # Sender scope: HSC, Group allowed scope: MA2 (HSC, S_PAKNING, HCC)
    # Effective scope = sender & group = HSC
    sender_scope = frozenset({"HSC"})
    group_scope = frozenset({"HSC", "S_PAKNING", "HCC"})
    effective_scope = sender_scope & group_scope
    assert effective_scope == frozenset({"HSC"})

    answer = _ask_helper("list pompa di ma2", scope=effective_scope)
    assert "212-P-01A" not in answer.answer
    assert "213-P-05A" not in answer.answer


def test_auth_24_ma2_query_cannot_leak_unauthorized_ma2_area():
    answer = _ask_helper("list pompa di ma2", scope=frozenset({"HSC"}))
    assert "213-P-05A" not in answer.answer
    assert "HCC" not in answer.answer


# ==============================================================================
# 25-27: SEAL SEMANTICS
# ==============================================================================

def test_semantics_25_current_seal_distinct_from_configured_seal():
    # 211-P-10B has no confirmed installation record
    answer = _ask_helper("211-P-10B area mana")
    assert answer.kind == FACT
    assert "Current Seal: N/A" in answer.answer


def test_semantics_26_current_seal_distinct_from_compatibility():
    # 211-P-10A has confirmed seal T48LP
    answer = _ask_helper("211-P-10A area mana")
    assert answer.kind == FACT
    assert "Current Seal: T48LP" in answer.answer


def test_semantics_27_stock_is_not_interpreted_as_installation():
    # When pump has stock but no confirmed installation, current seal is N/A while stock is displayed
    pumps = [{"tag_number": "211-P-99A", "area": "HSC", "status": "ACTIVE"}]
    pools = [
        {
            "stock_pool_id": "POOL-99",
            "seal_type": "T60",
            "quantity_available": 5,
            "applications": [{"equipment_tag": "211-P-99A"}],
        }
    ]
    seals = {"211-P-99A": None}
    answer = _ask_helper("211-P-99A area mana", pumps=pumps, pools=pools, seals=seals)
    assert answer.kind == FACT
    assert "Current Seal: N/A" in answer.answer
    assert "Seal Stock: 5" in answer.answer


# ==============================================================================
# 28-35: REGRESSIONS & TAG NORMALIZATION
# ==============================================================================

def test_regression_28_existing_stock_query_routes_to_inventory():
    assert _detect_intent("ada stock untuk 211p10a") == "inventory"
    assert _detect_intent("stok seal 211-P-10A berapa?") == "inventory"


def test_regression_29_pm_and_cm_unchanged():
    assert _detect_intent("PM terakhir 211-P-10A") == "pm"
    assert _detect_intent("kapan PM terakhir?") == "pm"
    assert _detect_intent("riwayat CM 211-P-10A") == "cm"


def test_regression_30_history_unchanged():
    assert _detect_intent("riwayat pemeliharaan 211-P-10A") == "pump_history"
    assert _detect_intent("history 211-P-10A") == "pump_history"


def test_regression_31_installation_unchanged():
    assert _detect_intent("kapan seal terakhir dipasang?") == "installation"
    assert _detect_intent("instalasi seal 211-P-10A") == "installation"


def test_regression_32_work_orders_unchanged():
    assert _detect_intent("work order aktif 211-P-10A") == "work_orders"
    assert _detect_intent("ada work order apa?") == "work_orders"


def test_regression_33_recommendation_unchanged():
    assert _detect_intent("rekomendasi untuk 211-P-10A") == "recommendation"


def test_regression_34_existing_fleet_intents_unchanged():
    assert _detect_intent("pompa mana yang paling sering bocor?") == "condition_monitoring"
    assert _detect_intent("pompa apa yang overdue PM?") == "fleet_pm_overdue"


def test_regression_35_tag_normalization_unchanged():
    assert _normalize_pump_tag("211p10a") == "211-P-10A"
    assert _normalize_pump_tag("110P12B") == "110-P-12B"
    assert _normalize_pump_tag("211-P-10A") == "211-P-10A"
    extracted = _extract_pump_tags("tolong cek 211p10a dan 110-P-12B")
    assert extracted == ["211-P-10A", "110-P-12B"]


# ==============================================================================
# 36-39: FORMATTING & OPERATIONAL RESPONSES
# ==============================================================================

def test_formatting_36_indonesian_concise_card():
    answer = _ask_helper("211-P-10A area mana")
    assert answer.kind == FACT
    expected_lines = [
        "211-P-10A",
        "Area: HSC",
        "MA: MA2",
        "Status: Active",
        "Current Seal: T48LP",
        "Seal Stock: 2",
    ]
    assert answer.answer == "\n".join(expected_lines)


def test_formatting_37_s_pakning_displays_as_human_label():
    assert format_area_display("S_PAKNING") == "S. PAKNING"
    assert normalize_area_token("S. PAKNING") == "S_PAKNING"
    assert normalize_area_token("SPK") == "S_PAKNING"

    answer = _ask_helper("212-P-01A area mana")
    assert "Area: S. PAKNING" in answer.answer
    assert "MA: MA2" in answer.answer


def test_formatting_38_large_result_safely_truncated():
    # Fleet with 30 pumps in HSC
    many_pumps = [
        {"tag_number": f"211-P-{i:02d}A", "area": "HSC", "status": "ACTIVE"}
        for i in range(1, 31)
    ]
    answer = _ask_helper("pompa hsc", pumps=many_pumps)
    assert answer.kind == FACT
    assert "Pompa HSC — 30" in answer.answer
    assert "Menampilkan 25 dari 30 pompa." in answer.answer
    assert "Gunakan filter Area untuk mempersempit hasil." in answer.answer
    # 25 bullets
    assert answer.answer.count("• 211-P-") == 25


def test_formatting_39_count_equals_actual_scoped_result():
    answer = _ask_helper("berapa pompa di HCC")
    assert answer.kind == FACT
    assert answer.answer == "Terdapat 2 pompa di HCC."
    assert answer.evidence[0]["value"] == "2"

    answer_ma2 = _ask_helper("berapa pompa MA2")
    assert answer_ma2.kind == FACT
    assert answer_ma2.answer == "Terdapat 5 pompa di MA2."
    assert answer_ma2.evidence[0]["value"] == "5"


def test_multiple_tags_asks_to_select_single_tag():
    answer = _ask_helper("211-P-10A atau 110-P-12B area mana")
    assert answer.kind == DATA_GAP
    assert "Saya menemukan beberapa tag pompa di pertanyaan itu" in answer.answer
