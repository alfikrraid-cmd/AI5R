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

    # Scope only
    res = service._build_where_clauses(scope=frozenset(["HCC", "HOC"]))
    assert "p.area IN ('HCC', 'HOC')" in res

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
    assert "p.area = 'HCC'" in res
    assert "p.tag_number = '101-P-10A'" in res
    assert "r.reading_date::date >= '2026-07-01'::date" in res
    assert "r.reading_date::date <= '2026-07-31'::date" in res


def test_get_filter_options():
    query_map = {
        "SELECT area, count(*)": [{"area": "HCC", "pump_count": 82}],
        "SELECT tag_number, area": [{"tag_number": "101-P-10A", "area": "HCC", "pump_type": "OH"}],
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
        "FROM pm_schedule": [{"c": 0}],
        "FROM work_order": [{"breakdowns": 0}],
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
    assert summary["seal_replacements_count"] is None
    assert summary["mtbsr_days"] is None
    assert summary["has_replacement_data"] is False


def test_get_material_analytics_unpopulated():
    query_map = {
        "FROM internal_component_stock": [{"c": 0}],
    }
    runner = FakeDatabaseRunner(query_map)
    service = LTSAAnalyticsService(runner)

    result = service.get_material_analytics()
    assert result["has_data"] is False
    assert result["summary"]["total_items_consumed"] is None
    assert "not yet ingested" in result["message"]

