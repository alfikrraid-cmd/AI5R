"""MWO-LTSA-FLEET-ANALYTICS-001 -- regression + N+1 proof for the new
fleet-wide analytics queries (temperature/vibration ranking, current vs.
historical leak, explicit stock-state semantics, overdue PM), exercised
through ask_copilot() end-to-end with fakes only at the gateway/repository
boundary -- same discipline as test_fleet_attention_query.py's own
fixture. Every fake tracks call counts so the N+1 test can prove the
batch fetch happens ONCE per fleet query, never once per pump.
"""

from datetime import date, timedelta

from API.copilot_ask_service import DATA_GAP, FACT, ask_copilot

TODAY = date.today()
RECENT = (TODAY - timedelta(days=5)).isoformat()
OLD = (TODAY - timedelta(days=90)).isoformat()
IN_WINDOW = (TODAY - timedelta(days=100)).isoformat()  # inside "1 year ago" window
OUTSIDE_WINDOW = (TODAY - timedelta(days=400)).isoformat()  # outside it


class FakePumpGateway:
    def __init__(self, pumps):
        self._pumps = pumps

    def list_pumps(self):
        return {"success": True, "data": self._pumps}


class FakeCMONRepository:
    """MWO-LTSA-FLEET-ANALYTICS-001 readiness closure -- shaped to match
    the REAL condition_monitoring_reading_repository.list_all()'s own
    return contract ({"success", "data", "count", "total", ...}, verified
    directly against production), not a bare list -- a bare-list fake
    here previously masked a real bug where build_fleet_data_batch()
    silently produced an empty cmon_by_tag against real production data."""

    def __init__(self, rows):
        self._rows = rows
        self.calls = 0

    def list_all(self, *, scope=None, limit=20000, offset=0):
        self.calls += 1
        rows = list(self._rows)
        return {"success": True, "message": "ok", "count": len(rows), "data": rows, "total": len(rows)}


class FakePMOccurrenceRepository:
    def __init__(self, rows=()):
        self._rows = rows
        self.calls = 0

    def list_all(self, *, scope=None, limit=20000, offset=0):
        self.calls += 1
        return list(self._rows)


class FakeListRepository:
    """list_X(*, scope=None) -> {"success": True, "data": rows} shaped
    fake, matching cm_report_repository/pm_schedule_repository's own
    contract."""

    def __init__(self, rows=()):
        self.calls = 0
        self._rows = rows

    def _list(self, *, scope=None):
        self.calls += 1
        return {"success": True, "data": self._rows}

    list_cm_reports = _list
    list_pm_schedules = _list


class FakeSealPumpCompatibilityGateway:
    def __init__(self, rows=()):
        self._rows = rows
        self.calls = 0

    def list_seal_pump_compatibilities(self):
        self.calls += 1
        return {"data": self._rows}


class FakeSealGateway:
    def __init__(self, rows=()):
        self._rows = rows
        self.calls = 0

    def list_seals(self):
        self.calls += 1
        return {"data": self._rows}


class FakeStockRepository:
    def __init__(self, pools=()):
        self._pools = pools
        self.calls = 0

    def list_pools(self, limit=200):
        self.calls += 1
        return {"success": True, "data": self._pools}


def _pump(tag, area="FRAKSINASI"):
    return {"tag_number": tag, "area": area, "status": "Active"}


def _cmon(tag, reading_date, **fields):
    row = {"asset_code": tag, "reading_date": reading_date, "condition_monitoring_reading_code": f"CMONR-{tag}-{reading_date}"}
    row.update(fields)
    return row


class _Fixture:
    def __init__(
        self,
        pumps,
        cmon_rows=(),
        pm_schedules=(),
        compatibilities=(),
        seals=(),
        stock_pools=(),
    ):
        self.pump_gateway = FakePumpGateway(pumps)
        self.cmon_repo = FakeCMONRepository(cmon_rows)
        self.pm_repo = FakePMOccurrenceRepository()
        self.cm_report_repo = FakeListRepository(())
        self.pm_schedule_repo = FakeListRepository(pm_schedules)
        self.compat_gateway = FakeSealPumpCompatibilityGateway(compatibilities)
        self.seal_gateway = FakeSealGateway(seals)
        self.stock_repo = FakeStockRepository(stock_pools)

    def ask(self, question, *, language="en", scope=None):
        return ask_copilot(
            question, None, scope,
            pump_gateway=self.pump_gateway,
            maintenance_history_gateway=None,
            work_order_gateway=None,
            installation_gateway=None,
            ltsa_knowledge_service=None,
            equipment_timeline_service=None,
            condition_monitoring_reading_gateway=None,
            installation_report_repository=None,
            mechanical_seal_stock_repository=self.stock_repo,
            condition_monitoring_reading_repository=self.cmon_repo,
            fleet_executive_summary_service=None,
            pm_occurrence_repository=self.pm_repo,
            cm_report_repository=self.cm_report_repo,
            pm_schedule_repository=self.pm_schedule_repo,
            seal_pump_compatibility_gateway=self.compat_gateway,
            seal_gateway=self.seal_gateway,
            language=language,
        )


# -- A. Temperature ranking ---------------------------------------------------


def test_temperature_ranking_returns_highest_pump_with_measurement_point_unit_and_date():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_rows=[
            _cmon("PUMP-A", RECENT, suction_temp=176.0),
            _cmon("PUMP-B", RECENT, suction_temp=90.0),
        ],
    )
    answer = fixture.ask("Pompa mana yang temperaturnya paling tinggi?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "176.0" in answer.answer
    assert "°C" in answer.answer
    assert "Suction Temp" in answer.answer
    assert answer.answer.index("PUMP-A") < answer.answer.index("PUMP-B")
    assert "Evaluated: 2 pump(s)" in answer.answer


# -- B. Temperature synonym ("suhunya") ---------------------------------------


def test_temperature_synonym_suhunya_routes_and_answers_identically():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_rows=[
            _cmon("PUMP-A", RECENT, suction_temp=176.0),
            _cmon("PUMP-B", RECENT, suction_temp=90.0),
        ],
    )
    answer = fixture.ask("Pompa mana yang suhunya paling tinggi?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "176.0" in answer.answer


# -- C. Vibration ranking ------------------------------------------------------


def test_vibration_ranking_excludes_pumps_with_no_vibration_data_but_counts_them():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B"), _pump("PUMP-C")],
        cmon_rows=[
            _cmon("PUMP-A", RECENT, vertical_vibration_de=8.2),
            _cmon("PUMP-B", RECENT, vertical_vibration_de=3.1),
            _cmon("PUMP-C", RECENT, suction_temp=50.0),  # no vibration field at all
        ],
    )
    answer = fixture.ask("Pompa mana yang vibrationnya paling tinggi?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "mm/s" in answer.answer
    assert "PUMP-C" not in answer.answer
    assert "Evaluated: 3 pump(s)" in answer.answer
    assert "With Vibration data: 2" in answer.answer


def test_vibration_synonym_getarannya_routes_and_answers_identically():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_rows=[
            _cmon("PUMP-A", RECENT, vertical_vibration_de=8.2),
            _cmon("PUMP-B", RECENT, vertical_vibration_de=3.1),
        ],
    )
    answer = fixture.ask("Pompa mana yang getarannya paling tinggi?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "8.2" in answer.answer


# -- D. Current leak ------------------------------------------------------------


def test_current_leak_returns_only_pumps_with_active_leak_evidence():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_rows=[
            _cmon("PUMP-A", RECENT, mechanical_seal_leak_de=True, finding="Leak at sleeve"),
            _cmon("PUMP-B", RECENT, mechanical_seal_leak_de=False),
        ],
    )
    answer = fixture.ask("Pompa mana yang sealnya bocor sekarang?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "PUMP-B" not in answer.answer


def test_plain_bocor_query_uses_current_leak_not_historical_frequency():
    fixture = _Fixture(
        pumps=[_pump("PUMP-OLD"), _pump("PUMP-CURRENT")],
        cmon_rows=[
            _cmon("PUMP-OLD", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-OLD", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-CURRENT", RECENT, mechanical_seal_leak_de=True, finding="Active leak"),
        ],
    )
    answer = fixture.ask("Pompa mana yang bocor?")
    assert answer.kind == FACT
    assert "PUMP-CURRENT" in answer.answer
    assert "PUMP-OLD" not in answer.answer


# -- E. Historical leak frequency (1yr, count only inside period) -------------


def test_historical_leak_frequency_counts_only_events_inside_the_period():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_rows=[
            _cmon("PUMP-A", IN_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-A", IN_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-A", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),  # must NOT count
        ],
    )
    answer = fixture.ask("Pompa mana yang paling sering bocor setahun terakhir?")
    assert answer.kind == FACT
    assert "PUMP-A" in answer.answer
    assert "2 leak event(s)" in answer.answer
    assert "3 leak event(s)" not in answer.answer


# -- F. Current-vs-historical negative test ------------------------------------


def test_many_old_leaks_never_outrank_a_current_leak_for_bocor_sekarang_query():
    fixture = _Fixture(
        pumps=[_pump("PUMP-OLD"), _pump("PUMP-CURRENT")],
        cmon_rows=[
            _cmon("PUMP-OLD", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-OLD", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-OLD", OUTSIDE_WINDOW, mechanical_seal_leak_de=True),
            _cmon("PUMP-CURRENT", RECENT, mechanical_seal_leak_de=True, finding="Active leak"),
        ],
    )
    answer = fixture.ask("Pompa mana yang sealnya bocor sekarang?")
    assert answer.kind == FACT
    assert "PUMP-CURRENT" in answer.answer
    assert "PUMP-OLD" not in answer.answer


# -- G. Zero stock (ZERO_STOCK only) -------------------------------------------


def test_zero_stock_query_returns_only_zero_stock_pumps():
    fixture = _Fixture(
        pumps=[_pump("PUMP-ZERO"), _pump("PUMP-OK"), _pump("PUMP-NO-RECORD")],
        compatibilities=[
            {"pump_tag_number": "PUMP-ZERO", "seal_code": "T48MP"},
            {"pump_tag_number": "PUMP-OK", "seal_code": "T48MP"},
            {"pump_tag_number": "PUMP-NO-RECORD", "seal_code": "SC-999"},
        ],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0,
                "applications": [{"equipment_tag": "PUMP-ZERO"}],
            },
            {
                "stock_pool_id": "POOL-2", "seal_type": "T48MP", "quantity_available": 5,
                "applications": [{"equipment_tag": "PUMP-OK"}],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang stock sealnya 0?")
    assert answer.kind == FACT
    assert "PUMP-ZERO" in answer.answer
    assert "PUMP-OK" not in answer.answer
    assert "PUMP-NO-RECORD" not in answer.answer


# -- H. No stock record (NO_STOCK_RECORD only) ---------------------------------


def test_no_stock_record_query_returns_only_missing_record_pumps():
    fixture = _Fixture(
        pumps=[_pump("PUMP-ZERO"), _pump("PUMP-NO-RECORD")],
        compatibilities=[
            {"pump_tag_number": "PUMP-ZERO", "seal_code": "T48MP"},
            {"pump_tag_number": "PUMP-NO-RECORD", "seal_code": "SC-999"},
        ],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}, {"seal_code": "SC-999", "seal_name": "SC-999 Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0,
                "applications": [{"equipment_tag": "PUMP-ZERO"}],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang tidak punya record stock seal?")
    assert answer.kind == FACT
    assert "PUMP-NO-RECORD" in answer.answer
    assert "PUMP-ZERO" not in answer.answer


# -- I. No spare (preserves all 3 reasons) -------------------------------------


def test_no_spare_seal_query_preserves_all_three_distinct_reasons():
    fixture = _Fixture(
        pumps=[_pump("PUMP-ZERO"), _pump("PUMP-NO-RECORD"), _pump("PUMP-NO-COMPAT"), _pump("PUMP-OK")],
        compatibilities=[
            {"pump_tag_number": "PUMP-ZERO", "seal_code": "T48MP"},
            {"pump_tag_number": "PUMP-NO-RECORD", "seal_code": "SC-999"},
            {"pump_tag_number": "PUMP-OK", "seal_code": "T48MP"},
        ],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}, {"seal_code": "SC-999", "seal_name": "SC-999 Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0,
                "applications": [{"equipment_tag": "PUMP-ZERO"}],
            },
            {
                "stock_pool_id": "POOL-2", "seal_type": "T48MP", "quantity_available": 5,
                "applications": [{"equipment_tag": "PUMP-OK"}],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang tidak punya spare seal?")
    assert answer.kind == FACT
    assert "PUMP-ZERO" in answer.answer
    assert "PUMP-NO-RECORD" in answer.answer
    assert "PUMP-NO-COMPAT" in answer.answer
    assert "PUMP-OK" not in answer.answer
    assert "Zero stock:" in answer.answer
    assert "No inventory record:" in answer.answer
    assert "No compatible seal mapped:" in answer.answer


def test_tidak_ada_stock_sealnya_preserves_all_three_distinct_reasons():
    fixture = _Fixture(
        pumps=[_pump("PUMP-ZERO"), _pump("PUMP-NO-RECORD"), _pump("PUMP-NO-COMPAT"), _pump("PUMP-OK")],
        compatibilities=[
            {"pump_tag_number": "PUMP-ZERO", "seal_code": "T48MP"},
            {"pump_tag_number": "PUMP-NO-RECORD", "seal_code": "SC-999"},
            {"pump_tag_number": "PUMP-OK", "seal_code": "T48MP"},
        ],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}, {"seal_code": "SC-999", "seal_name": "SC-999 Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0,
                "applications": [{"equipment_tag": "PUMP-ZERO"}],
            },
            {
                "stock_pool_id": "POOL-2", "seal_type": "T48MP", "quantity_available": 5,
                "applications": [{"equipment_tag": "PUMP-OK"}],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang tidak ada stock sealnya?")
    assert answer.kind == FACT
    assert "PUMP-ZERO" in answer.answer
    assert "PUMP-NO-RECORD" in answer.answer
    assert "PUMP-NO-COMPAT" in answer.answer
    assert "PUMP-OK" not in answer.answer
    assert "Zero stock:" in answer.answer
    assert "No inventory record:" in answer.answer
    assert "No compatible seal mapped:" in answer.answer


# -- J. Available-stock negative test ------------------------------------------


def test_available_stock_pump_never_appears_in_zero_stock_or_no_record_results():
    fixture = _Fixture(
        pumps=[_pump("PUMP-OK")],
        compatibilities=[{"pump_tag_number": "PUMP-OK", "seal_code": "T48MP"}],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5,
                "applications": [{"equipment_tag": "PUMP-OK"}],
            },
        ],
    )
    zero_answer = fixture.ask("Pompa mana yang stock sealnya 0?")
    assert zero_answer.kind == DATA_GAP
    assert "PUMP-OK" not in zero_answer.answer

    no_record_answer = fixture.ask("Pompa mana yang tidak punya record stock seal?")
    assert no_record_answer.kind == DATA_GAP
    assert "PUMP-OK" not in no_record_answer.answer


# -- K. Missing-inventory negative test ----------------------------------------


def test_missing_inventory_row_is_never_interpreted_as_zero():
    fixture = _Fixture(
        pumps=[_pump("PUMP-NO-RECORD")],
        compatibilities=[{"pump_tag_number": "PUMP-NO-RECORD", "seal_code": "SC-999"}],
        seals=[{"seal_code": "SC-999", "seal_name": "SC-999 Seal"}],
        stock_pools=[],  # no pool row at all for this seal
    )
    zero_answer = fixture.ask("Pompa mana yang stock sealnya 0?")
    # No real pool row exists -- must be classified NO_STOCK_RECORD, never
    # silently counted as ZERO_STOCK.
    assert zero_answer.kind == DATA_GAP
    assert "PUMP-NO-RECORD" not in zero_answer.answer

    no_record_answer = fixture.ask("Pompa mana yang tidak punya record stock seal?")
    assert no_record_answer.kind == FACT
    assert "PUMP-NO-RECORD" in no_record_answer.answer


# -- L. Compatibility safety test ----------------------------------------------


def test_compatible_seal_is_never_labeled_installed_in_stock_semantics_answer():
    fixture = _Fixture(
        pumps=[_pump("PUMP-ZERO")],
        compatibilities=[{"pump_tag_number": "PUMP-ZERO", "seal_code": "T48MP"}],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 0,
                "applications": [{"equipment_tag": "PUMP-ZERO"}],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang stock sealnya 0?")
    assert "installed" not in answer.answer.lower()
    assert "terpasang" not in answer.answer.lower()


# -- M. Overdue PM --------------------------------------------------------------


def test_overdue_pm_requires_canonical_schedule_evidence():
    overdue_due = (TODAY - timedelta(days=10)).isoformat()
    future_due = (TODAY + timedelta(days=30)).isoformat()
    fixture = _Fixture(
        pumps=[_pump("PUMP-OVERDUE"), _pump("PUMP-ON-TIME"), _pump("PUMP-UNSCHEDULED")],
        pm_schedules=[
            {"asset_code": "PUMP-OVERDUE", "pm_schedule_code": "S-1", "next_due": overdue_due, "status": "ACTIVE"},
            {"asset_code": "PUMP-ON-TIME", "pm_schedule_code": "S-2", "next_due": future_due, "status": "ACTIVE"},
        ],
    )
    answer = fixture.ask("Pompa mana yang overdue PM?")
    assert answer.kind == FACT
    assert "PUMP-OVERDUE" in answer.answer
    assert "PUMP-ON-TIME" not in answer.answer
    # No schedule row at all -- UNSCHEDULED, never fabricated as overdue.
    assert "PUMP-UNSCHEDULED" not in answer.answer


def test_overdue_pm_no_schedule_data_is_a_truthful_fact_not_fabricated():
    fixture = _Fixture(pumps=[_pump("PUMP-A")], pm_schedules=[])
    answer = fixture.ask("Pompa mana yang overdue PM?")
    assert answer.kind == FACT
    assert "PUMP-A" not in answer.answer


# -- Q. N+1 proof: batch fetch happens ONCE per fleet query, never per pump --


def test_fleet_analytics_batch_fetch_is_o1_not_per_pump():
    pumps = [_pump(f"PUMP-{i}") for i in range(15)]
    cmon_rows = [_cmon(f"PUMP-{i}", RECENT, suction_temp=50.0 + i) for i in range(15)]
    fixture = _Fixture(
        pumps=pumps,
        cmon_rows=cmon_rows,
        compatibilities=[{"pump_tag_number": f"PUMP-{i}", "seal_code": "T48MP"} for i in range(15)],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {
                "stock_pool_id": "POOL-1", "seal_type": "T48MP", "quantity_available": 5,
                "applications": [{"equipment_tag": f"PUMP-{i}"} for i in range(15)],
            },
        ],
    )
    answer = fixture.ask("Pompa mana yang temperaturnya paling tinggi?")
    assert answer.kind == FACT

    # Every batch-fetch source called EXACTLY ONCE for the whole fleet,
    # regardless of pump count -- the actual fix this MWO exists for.
    assert fixture.cmon_repo.calls == 1
    assert fixture.pm_repo.calls == 1
    assert fixture.cm_report_repo.calls == 1
    assert fixture.pm_schedule_repo.calls == 1
    assert fixture.compat_gateway.calls == 1
    assert fixture.seal_gateway.calls == 1
    assert fixture.stock_repo.calls == 1

    print(
        f"PUMPS_SCANNED={len(pumps)} "
        f"CMON_REPO_CALLS={fixture.cmon_repo.calls} "
        f"PM_REPO_CALLS={fixture.pm_repo.calls} "
        f"CM_REPORT_REPO_CALLS={fixture.cm_report_repo.calls} "
        f"PM_SCHEDULE_REPO_CALLS={fixture.pm_schedule_repo.calls} "
        f"COMPAT_GATEWAY_CALLS={fixture.compat_gateway.calls} "
        f"SEAL_GATEWAY_CALLS={fixture.seal_gateway.calls} "
        f"STOCK_REPO_CALLS={fixture.stock_repo.calls}"
    )


def test_fleet_priority_query_uses_batch_path_when_wired_gateway_calls_o1():
    """The SAME O(1) proof, but for FleetReliabilityService.
    list_pump_knowledge_fast()/FleetExecutiveSummaryService.build() --
    the actual "Pompa mana yang perlu perhatian hari ini?" path -- via
    the real production wiring pattern (batch-sourcing deps supplied to
    the constructor), not ask_copilot()'s fleet_priority branch (which
    needs a FleetExecutiveSummaryService, out of this file's scope)."""
    from API.fleet_reliability_service import FleetReliabilityService

    pumps = [_pump(f"PUMP-{i}") for i in range(15)]
    cmon_rows = [_cmon(f"PUMP-{i}", RECENT, mechanical_seal_leak_de=True) for i in range(15)]
    fixture = _Fixture(pumps=pumps, cmon_rows=cmon_rows)

    service = FleetReliabilityService(
        pump_gateway=fixture.pump_gateway,
        condition_monitoring_reading_repository=fixture.cmon_repo,
        cm_report_repository=fixture.cm_report_repo,
        pm_occurrence_repository=fixture.pm_repo,
        pm_schedule_repository=fixture.pm_schedule_repo,
        seal_pump_compatibility_gateway=fixture.compat_gateway,
        seal_gateway=fixture.seal_gateway,
        mechanical_seal_stock_repository=fixture.stock_repo,
    )
    knowledge = service.list_pump_knowledge_fast()
    assert len(knowledge) == len(pumps)
    assert fixture.cmon_repo.calls == 1
    assert fixture.pm_repo.calls == 1
    assert fixture.cm_report_repo.calls == 1
    assert fixture.pm_schedule_repo.calls == 1
    assert fixture.compat_gateway.calls == 1
    assert fixture.seal_gateway.calls == 1
    assert fixture.stock_repo.calls == 1
