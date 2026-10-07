import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

CORE_SERVICES_DIR = Path(__file__).resolve().parents[1]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.ltsa_analytics_service import LTSAAnalyticsService


class FakeDatabaseRunner:
    def __init__(self, query_map=None):
        self.queries = []
        self.query_map = query_map or {}

    def query_scalar(self, sql: str) -> str:
        self.queries.append(sql)
        for pattern, response in self.query_map.items():
            if pattern in sql:
                return json.dumps(response)
        return "[]"


def test_where_clause_builder():
    runner = FakeDatabaseRunner()
    service = LTSAAnalyticsService(runner)

    # Empty
    assert service._build_where_clauses() == ""

    # Scope only -- compared on the canonical area (aliases normalized)
    res = service._build_where_clauses(scope=frozenset(["HCC", "HOC"]))
    assert "END) IN ('HCC', 'HOC')" in res
    assert "WHEN 'SPK' THEN 'S_PAKNING'" in res
    assert "p.area IN" not in res

    # Empty scope (no access)
    res = service._build_where_clauses(scope=frozenset())
    assert "WHERE FALSE" in res

    # Area + Pump tag + Dates
    res = service._build_where_clauses(
        pump_alias="p",
        record_alias="r",
        date_col="reading_date",
        area="HCC",
        pump_tag="101-P-10A",
        start_date="2026-07-01",
        end_date="2026-07-31",
    )
    assert "END) = 'HCC'" in res
    assert "p.tag_number = '101-P-10A'" in res
    assert "r.reading_date::date >= '2026-07-01'::date" in res
    assert "r.reading_date::date <= '2026-07-31'::date" in res


def test_get_filter_options():
    query_map = {
        "as area, count(*) as pump_count": [{"area": "HCC", "pump_count": 82}],
        "SELECT tag_number, area": [{"tag_number": "101-P-10A", "area": "HCC", "canonical_area": "HCC", "pump_type": "OH"}],
        "SELECT \n                min(dt)": [{"min_date": "2026-07-01", "max_date": "2026-07-31"}],
    }
    runner = FakeDatabaseRunner(query_map)
    service = LTSAAnalyticsService(runner)

    filters = service.get_filter_options(scope=frozenset(["HCC"]))
    assert len(filters["areas"]) == 1
    assert filters["areas"][0]["area"] == "HCC"
    assert filters["date_range"]["min_date"] == "2026-07-01"


def test_get_executive_analytics_unknown_neq_zero():
    query_map = {
        "count(*) as total_pumps": [{"total_pumps": 244, "active_pumps": 0}],
        "monitored_pumps": [
            {
                "monitored_pumps": 211,
                "cmon_readings": 596,
                "seal_leaks": 52,
                "de_leaks": 45,
                "nde_leaks": 9,
            }
        ],
        "pm_executed": [{"pm_pumps": 53, "pm_executed": 53, "pm_done": 53}],
        "FROM pm_schedule": [{"pm_scheduled": 0}],
    }
    runner = FakeDatabaseRunner(query_map)
    service = LTSAAnalyticsService(runner)

    result = service.get_executive_analytics()
    kpis = result["kpis"]

    # Strict UNKNOWN != ZERO checks
    assert kpis["total_pumps"] == 244
    assert kpis["active_pumps"] is None  # All status=UNKNOWN -> None, not 0
    assert kpis["monitored_pumps"] == 211
    assert kpis["pm_executed_count"] == 53
    assert kpis["confirmed_seal_leaks"] == 52
    assert kpis["pm_scheduled_count"] is None  # Schedule table empty -> None, not 0
    assert kpis["pm_compliance_percent"] is None  # Unknown compliance
    assert kpis["fleet_mtbf_days"] is None  # Insufficient failures -> None, not 0
    assert kpis["fleet_mttr_hours"] is None
    assert kpis["fleet_availability"] is None
    # TD-020: no work_order classification column exists -> never queried,
    # breakdowns UNKNOWN (None), never 0.
    assert kpis["breakdown_count"] is None
    assert not any("work_type" in q or "FROM work_order" in q for q in runner.queries)


def test_get_seal_analytics_unpopulated():
    query_map = {
        "FROM seal_lifecycle_event": [{"c": 0}],
        "FROM seal_stock": [{"c": 0}],
        "FROM seal_registry": [{"c": 0}],
    }
    runner = FakeDatabaseRunner(query_map)
    service = LTSAAnalyticsService(runner)

    result = service.get_seal_analytics()
    summary = result["summary"]
    # No pump-bound INSTALL events -> no recorded data (None), and no
    # "replacement" metric at all.
    assert summary["seal_installations_count"] is None
    assert summary["has_installation_data"] is False
    assert "seal_replacements_count" not in summary
    assert "mtbsr_days" not in summary


def test_get_material_analytics_unpopulated():
    query_map = {
        "FROM internal_component_stock": [{"c": 0}],
    }
    runner = FakeDatabaseRunner(query_map)
    service = LTSAAnalyticsService(runner)

    result = service.get_material_analytics(include_internal_components=True)
    assert result["has_data"] is False
    assert result["summary"]["total_items_consumed"] is None
    assert "not yet ingested" in result["message"]



# --- LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B ------------------------------

PERTAMINA_ALL = frozenset({"HOC", "HSC", "S_PAKNING", "HCC", "OM", "UTL"})


def test_canonical_area_sql_maps_production_aliases_and_nothing_else():
    from API.pump_area_scope import _AREA_TOKEN_MAP, canonical_area_sql

    expr = canonical_area_sql("p.area")
    for alias, code in (("SPK", "S_PAKNING"), ("OIL MOVEMENT", "OM"), ("UTILITIES", "UTL"), ("S. PAKNING", "S_PAKNING")):
        assert f"WHEN '{alias}' THEN '{code}'" in expr
    # Every alias comes from the single Python map -- no second vocabulary.
    assert expr.count(" WHEN ") == len(_AREA_TOKEN_MAP)
    for outside in ("REAKTOR", "FRAKSINASI", "DCU", "AMINE", "CDU", "DHDT", "H2 PLAN", "ITY", "PL1", "PL2", "VACUUM"):
        assert f"'{outside}'" not in expr


def test_pertamina_all_scope_clause_is_the_finite_six_never_unrestricted():
    service = LTSAAnalyticsService(FakeDatabaseRunner())
    res = service._build_where_clauses(scope=PERTAMINA_ALL)
    assert "END) IN ('HCC', 'HOC', 'HSC', 'OM', 'S_PAKNING', 'UTL')" in res


def test_pm_compliance_is_none_when_scope_has_no_pm_schedule():
    runner = FakeDatabaseRunner(
        {
            "count(*) as total_pumps": [{"total_pumps": 54, "active_pumps": 54}],
            "pm_executed": [{"pm_pumps": 5, "pm_executed": 5, "pm_done": 5}],
            "FROM pm_schedule": [{"pm_scheduled": 0}],
        }
    )
    kpis = LTSAAnalyticsService(runner).get_executive_analytics(scope=frozenset({"HOC"}))["kpis"]
    assert kpis["pm_scheduled_count"] is None
    assert kpis["pm_compliance_percent"] is None  # never 100.0 for "no schedule"
    sched_sql = next(q for q in runner.queries if "FROM pm_schedule" in q)
    assert "IN ('HOC')" in sched_sql  # existence is checked inside the scope


def test_pm_compliance_uses_scoped_schedules_when_present():
    runner = FakeDatabaseRunner(
        {
            "pm_executed": [{"pm_pumps": 2, "pm_executed": 3, "pm_done": 2}],
            "FROM pm_schedule": [{"pm_scheduled": 4}],
        }
    )
    kpis = LTSAAnalyticsService(runner).get_executive_analytics(scope=frozenset({"HOC"}))["kpis"]
    assert kpis["pm_scheduled_count"] == 4
    assert kpis["pm_compliance_percent"] == 50.0


def test_scoped_seal_analytics_hide_fleet_wide_stock_and_registry():
    runner = FakeDatabaseRunner({"FROM seal_stock": [{"c": 40}], "FROM seal_registry": [{"c": 61}]})
    summary = LTSAAnalyticsService(runner).get_seal_analytics(scope=PERTAMINA_ALL)["summary"]
    assert summary["total_stock_units"] is None
    assert summary["total_registered_seals"] is None
    assert summary["fleet_inventory_available"] is False
    assert not any("FROM seal_stock" in q or "FROM seal_registry" in q for q in runner.queries)


def test_unrestricted_unfiltered_seal_analytics_keep_fleet_inventory():
    runner = FakeDatabaseRunner({"FROM seal_stock": [{"c": 40}], "FROM seal_registry": [{"c": 61}]})
    summary = LTSAAnalyticsService(runner).get_seal_analytics(scope=None)["summary"]
    assert summary["total_stock_units"] == 40
    assert summary["total_registered_seals"] == 61
    assert summary["fleet_inventory_available"] is True


def test_seal_installations_count_only_pump_bound_install_events_in_scope():
    runner = FakeDatabaseRunner({"FROM seal_lifecycle_event": [{"c": 3}]})
    summary = LTSAAnalyticsService(runner).get_seal_analytics(scope=frozenset({"HCC"}))["summary"]
    assert summary["seal_installations_count"] == 3
    sql = next(q for q in runner.queries if "FROM seal_lifecycle_event" in q)
    assert "JOIN ltsa_pumps p ON p.tag_number = e.pump_tag_number" in sql  # NULL pump tags excluded
    assert "e.event_type = 'INSTALL'" in sql
    assert "IN ('HCC')" in sql
    assert "REPLACEMENT" not in sql and "INSTALLATION" not in sql


def test_material_analytics_withhold_internal_component_stock_without_permission_or_with_scope():
    for kwargs in ({"include_internal_components": False}, {"include_internal_components": True, "scope": PERTAMINA_ALL}):
        runner = FakeDatabaseRunner({"FROM internal_component_stock": [{"c": 12}]})
        result = LTSAAnalyticsService(runner).get_material_analytics(**kwargs)
        assert result["has_data"] is False
        assert result["summary"]["total_items_consumed"] is None
        assert not any("internal_component_stock" in q for q in runner.queries)


def test_material_analytics_reads_internal_component_stock_for_permitted_unrestricted_caller():
    runner = FakeDatabaseRunner({"FROM internal_component_stock": [{"c": 12}]})
    result = LTSAAnalyticsService(runner).get_material_analytics(include_internal_components=True)
    assert result["summary"]["total_items_consumed"] == 12
