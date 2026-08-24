# MWO-LTSA-DASHBOARD-RECOVERY-001 -- BasicFleetOverviewService: bounded
# fleet summary from canonical bulk-list gateways only. These tests prove
# exactly one call per gateway (never a per-pump loop), correct area/
# asset_code scoping, evidence-only distributions, and graceful
# degradation when a gateway is unreachable.

import sys
from pathlib import Path

CORE_SERVICES_DIR = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_DIR))

from API.basic_fleet_overview_service import BasicFleetOverview, BasicFleetOverviewService
from API.pump_contract_area import UNCLASSIFIED, resolve_contract_area


class FakeListGateway:
    def __init__(self, records, list_method_name, fail=False):
        self._records = records
        self._list_method_name = list_method_name
        self._fail = fail
        self.calls = 0
        setattr(self, list_method_name, self._list)

    def _list(self):
        self.calls += 1
        if self._fail:
            raise OSError("gateway unreachable")
        return {"success": True, "data": self._records}


def _service(pumps=(), work_orders=(), pm_schedules=(), cm_reports=(), seal_stocks=(), **fail_flags):
    pump_gw = FakeListGateway(list(pumps), "list_pumps", fail=fail_flags.get("pumps", False))
    wo_gw = FakeListGateway(list(work_orders), "list_work_orders", fail=fail_flags.get("work_orders", False))
    pm_gw = FakeListGateway(list(pm_schedules), "list_pm_schedules", fail=fail_flags.get("pm_schedules", False))
    cm_gw = FakeListGateway(list(cm_reports), "list_cm_reports", fail=fail_flags.get("cm_reports", False))
    seal_gw = FakeListGateway(list(seal_stocks), "list_seal_stocks", fail=fail_flags.get("seal_stocks", False))
    service = BasicFleetOverviewService(
        pump_gateway=pump_gw,
        work_order_gateway=wo_gw,
        pm_schedule_gateway=pm_gw,
        cm_report_gateway=cm_gw,
        seal_stock_gateway=seal_gw,
    )
    return service, {"pumps": pump_gw, "work_orders": wo_gw, "pm_schedules": pm_gw, "cm_reports": cm_gw, "seal_stocks": seal_gw}


def test_calls_each_gateway_exactly_once_no_per_pump_fanout():
    pumps = [{"tag_number": f"P-{i}", "area": "Reaktor", "status": "ACTIVE"} for i in range(5)]
    service, gws = _service(pumps=pumps)

    service.build()

    assert gws["pumps"].calls == 1
    assert gws["work_orders"].calls == 1
    assert gws["pm_schedules"].calls == 1
    assert gws["cm_reports"].calls == 1
    assert gws["seal_stocks"].calls == 1


def test_pump_count_and_distributions_from_bulk_pump_list():
    pumps = [
        {"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"},
        {"tag_number": "P-B", "area": "Reaktor", "status": "STANDBY"},
        {"tag_number": "P-C", "area": "Utility", "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.pump_count == 3
    assert result.area_distribution == {"Reaktor": 2, "Utility": 1}
    assert result.status_distribution == {"ACTIVE": 2, "STANDBY": 1}


def test_pumps_missing_area_or_status_are_excluded_from_that_distribution_not_fabricated():
    pumps = [
        {"tag_number": "P-A", "area": "Reaktor", "status": None},
        {"tag_number": "P-B", "area": None, "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.pump_count == 2
    assert result.area_distribution == {"Reaktor": 1}
    assert result.status_distribution == {"ACTIVE": 1}


def test_work_orders_scoped_to_known_pump_tags_via_asset_code():
    pumps = [{"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"}]
    work_orders = [
        {"work_order_code": "WO-1", "asset_code": "P-A", "status": "OPEN"},
        {"work_order_code": "WO-2", "asset_code": "NOT-A-PUMP", "status": "OPEN"},
    ]
    service, _ = _service(pumps=pumps, work_orders=work_orders)

    result = service.build()

    assert result.work_order_count == 1
    assert result.work_order_status_distribution == {"OPEN": 1}


def test_area_scope_filters_pumps_before_any_count_is_taken():
    pumps = [
        {"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"},
        {"tag_number": "P-B", "area": "Utility", "status": "ACTIVE"},
    ]
    work_orders = [
        {"work_order_code": "WO-1", "asset_code": "P-A", "status": "OPEN"},
        {"work_order_code": "WO-2", "asset_code": "P-B", "status": "OPEN"},
    ]
    service, _ = _service(pumps=pumps, work_orders=work_orders)

    result = service.build(scope=frozenset({"Reaktor"}))

    assert result.pump_count == 1
    assert result.area_distribution == {"Reaktor": 1}
    # P-B's work order must not leak through even though it was in the
    # unscoped work-order list -- P-B itself was filtered out of
    # scoped_tags before work orders were matched against it.
    assert result.work_order_count == 1


def test_pm_schedule_and_cm_report_counts_scoped_by_asset_code():
    pumps = [{"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"}]
    pm_schedules = [{"pm_schedule_code": "PM-1", "asset_code": "P-A"}]
    cm_reports = [
        {"cm_report_code": "CM-1", "asset_code": "P-A"},
        {"cm_report_code": "CM-2", "asset_code": "OTHER"},
    ]
    service, _ = _service(pumps=pumps, pm_schedules=pm_schedules, cm_reports=cm_reports)

    result = service.build()

    assert result.pm_schedule_count == 1
    assert result.cm_report_count == 1


def test_seal_stock_count_and_low_stock_from_quantity_and_reorder_point():
    seal_stocks = [
        {"seal_code": "SC-1", "quantity_on_hand": 2, "reorder_point": 5},
        {"seal_code": "SC-2", "quantity_on_hand": 10, "reorder_point": 5},
    ]
    service, _ = _service(seal_stocks=seal_stocks)

    result = service.build()

    assert result.seal_stock_count == 2
    assert result.low_stock_seal_count == 1


def test_low_stock_seal_count_is_none_when_no_record_has_both_fields():
    seal_stocks = [{"seal_code": "SC-1"}]
    service, _ = _service(seal_stocks=seal_stocks)

    result = service.build()

    assert result.seal_stock_count == 1
    assert result.low_stock_seal_count is None


def test_empty_fleet_returns_all_empty_and_zero_fields_never_fabricated():
    service, _ = _service()

    result = service.build()

    assert result == BasicFleetOverview(
        pump_count=0,
        area_distribution={},
        contract_area_distribution={
            "HOC": 0,
            "HSC & S. Pakning": 0,
            "HCC": 0,
            "OM & UTL": 0,
            UNCLASSIFIED: 0,
        },
        status_distribution={},
        work_order_count=0,
        work_order_status_distribution={},
        pm_schedule_count=0,
        cm_report_count=0,
        seal_stock_count=0,
        low_stock_seal_count=None,
    )


def test_pump_records_without_a_tag_number_are_skipped():
    pumps = [{"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"}, {"area": "Reaktor"}]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.pump_count == 1


def test_one_gateway_failing_does_not_break_the_others():
    pumps = [{"tag_number": "P-A", "area": "Reaktor", "status": "ACTIVE"}]
    seal_stocks = [{"seal_code": "SC-1", "quantity_on_hand": 1, "reorder_point": 5}]
    service, gws = _service(pumps=pumps, seal_stocks=seal_stocks)
    gws["work_orders"]._fail = True

    result = service.build()

    assert result.pump_count == 1
    assert result.work_order_count == 0
    assert result.seal_stock_count == 1
    assert result.low_stock_seal_count == 1


# MWO-LTSA-FLEET-CONTRACT-AREA-001 -- contract_area_distribution: explicit-
# token classification only, never inferred from tag-number prefix or any
# other signal. area_distribution (raw) is unchanged/untouched by this.


def test_contract_area_distribution_maps_the_seven_explicit_tokens():
    pumps = [
        {"tag_number": "P-1", "area": "HOC", "status": "ACTIVE"},
        {"tag_number": "P-2", "area": "HSC", "status": "ACTIVE"},
        {"tag_number": "P-3", "area": "SPK", "status": "ACTIVE"},
        {"tag_number": "P-4", "area": "S_PAKNING", "status": "ACTIVE"},
        {"tag_number": "P-5", "area": "HCC", "status": "ACTIVE"},
        {"tag_number": "P-6", "area": "OM", "status": "ACTIVE"},
        {"tag_number": "P-7", "area": "UTL", "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.contract_area_distribution == {
        "HOC": 1,
        "HSC & S. Pakning": 3,
        "HCC": 1,
        "OM & UTL": 2,
        UNCLASSIFIED: 0,
    }


def test_contract_area_distribution_sends_unknown_tokens_to_unclassified():
    pumps = [
        {"tag_number": "P-1", "area": "REAKTOR", "status": "ACTIVE"},
        {"tag_number": "P-2", "area": "CDU", "status": "ACTIVE"},
        {"tag_number": "P-3", "area": "FRAKSINASI", "status": "ACTIVE"},
        {"tag_number": "P-4", "area": None, "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.contract_area_distribution == {
        "HOC": 0,
        "HSC & S. Pakning": 0,
        "HCC": 0,
        "OM & UTL": 0,
        UNCLASSIFIED: 4,
    }


def test_contract_area_never_infers_from_tag_number_prefix():
    # Same tag-number prefix as an HCC-mapped sibling is NOT evidence --
    # REAKTOR must resolve Unclassified regardless of what its neighbors
    # under the same prefix are mapped to.
    pumps = [
        {"tag_number": "212-P-4A", "area": "REAKTOR", "status": "ACTIVE"},
        {"tag_number": "212-P-4B", "area": "HCC", "status": "ACTIVE"},
        {"tag_number": "212-P-4C", "area": "HCC", "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.contract_area_distribution["HCC"] == 2
    assert result.contract_area_distribution[UNCLASSIFIED] == 1


def test_raw_area_distribution_is_unchanged_by_contract_area_classification():
    pumps = [
        {"tag_number": "P-1", "area": "REAKTOR", "status": "ACTIVE"},
        {"tag_number": "P-2", "area": "HCC", "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert result.area_distribution == {"REAKTOR": 1, "HCC": 1}
    assert result.contract_area_distribution == {
        "HOC": 0,
        "HSC & S. Pakning": 0,
        "HCC": 1,
        "OM & UTL": 0,
        UNCLASSIFIED: 1,
    }


def test_contract_area_distribution_totals_reconcile_to_pump_count():
    pumps = [
        {"tag_number": "P-1", "area": "HOC", "status": "ACTIVE"},
        {"tag_number": "P-2", "area": "REAKTOR", "status": "ACTIVE"},
        {"tag_number": "P-3", "area": "OM", "status": "ACTIVE"},
        {"tag_number": "P-4", "area": None, "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build()

    assert sum(result.contract_area_distribution.values()) == result.pump_count == 4


def test_contract_area_distribution_respects_existing_area_scope_filtering():
    # Scope filtering happens on the raw `area` field before classification,
    # same choke point as area_distribution/status_distribution -- proving
    # contract_area_distribution doesn't bypass or duplicate scope logic.
    pumps = [
        {"tag_number": "P-A", "area": "HCC", "status": "ACTIVE"},
        {"tag_number": "P-B", "area": "OM", "status": "ACTIVE"},
    ]
    service, _ = _service(pumps=pumps)

    result = service.build(scope=frozenset({"HCC"}))

    assert result.pump_count == 1
    assert result.contract_area_distribution == {
        "HOC": 0,
        "HSC & S. Pakning": 0,
        "HCC": 1,
        "OM & UTL": 0,
        UNCLASSIFIED: 0,
    }


def test_resolve_contract_area_is_a_pure_explicit_token_lookup():
    assert resolve_contract_area("HOC") == "HOC"
    assert resolve_contract_area("HSC") == "HSC & S. Pakning"
    assert resolve_contract_area("SPK") == "HSC & S. Pakning"
    assert resolve_contract_area("S_PAKNING") == "HSC & S. Pakning"
    assert resolve_contract_area("HCC") == "HCC"
    assert resolve_contract_area("OM") == "OM & UTL"
    assert resolve_contract_area("UTL") == "OM & UTL"
    assert resolve_contract_area("REAKTOR") == UNCLASSIFIED
    assert resolve_contract_area("CDU") == UNCLASSIFIED
    assert resolve_contract_area(None) == UNCLASSIFIED
    assert resolve_contract_area("") == UNCLASSIFIED
    # Case-sensitive exact match only -- lowercase variants of a real
    # token are not silently normalized, per "map ONLY explicit tokens".
    assert resolve_contract_area("hoc") == UNCLASSIFIED
