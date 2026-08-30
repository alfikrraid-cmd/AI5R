"""MWO-LTSA-FLEET-ANALYTICS-001 readiness closure -- proves the fleet
query acknowledgement + webhook-retry-dedup mechanism (originally built
for fleet_priority alone, MWO-LTSA-FLEET-ATTENTION-001) now covers every
expensive, tag-less fleet-analytics query, that retrying the same inbound
WhatsApp message can never produce a duplicate final answer, and that
every one of these new query shapes is genuinely READ-ONLY (never
persists, never writes) all the way through process_inbound_message --
not just through ask_copilot() directly.
"""

from datetime import date, timedelta

from API.whatsapp_intake_service import (
    LTSAAIQueryDependencies,
    _asset_context_cache,
    _fleet_query_delivery_tracker,
    _is_expensive_fleet_query,
    process_inbound_message,
)

TODAY = date.today()
RECENT = (TODAY - timedelta(days=5)).isoformat()


# -- Test A: expensive-fleet-query classification -----------------------------


def test_every_named_fleet_intent_is_classified_expensive_when_tagless():
    assert _is_expensive_fleet_query("fleet_priority", None, "perlu perhatian hari ini?") is True
    assert _is_expensive_fleet_query("fleet_pm_overdue", None, "overdue PM?") is True
    assert _is_expensive_fleet_query("condition_monitoring", None, "temperaturnya paling tinggi?") is True
    assert _is_expensive_fleet_query("condition_monitoring", None, "vibrationnya paling tinggi?") is True
    assert _is_expensive_fleet_query("condition_monitoring", None, "sealnya bocor sekarang?") is True
    assert _is_expensive_fleet_query("condition_monitoring", None, "paling sering bocor setahun terakhir?") is True
    assert _is_expensive_fleet_query("inventory", None, "seal pompa mana yang ga ada stocknya?") is True


def test_single_equipment_reads_are_never_classified_expensive():
    assert _is_expensive_fleet_query("condition_monitoring", "211-P-13AR", "CMON terakhir 211-P-13AR") is False
    assert _is_expensive_fleet_query("pump_status", None, "status pompa") is False
    assert _is_expensive_fleet_query("inventory", "211-P-13AR", "stock seal 211-P-13AR") is False


def test_seal_code_keyed_inventory_lookup_is_not_classified_expensive():
    # A single Stock V1 pool lookup by seal code -- tag-less but NOT a
    # fleet scan, must stay on the fast, ordinary path.
    assert _is_expensive_fleet_query("inventory", None, "stok seal T48MP berapa?") is False


# -- Fixtures: fleet-analytics batch fakes + WhatsApp repository/identity ----


class FakePumpGateway:
    def __init__(self, pumps):
        self._pumps = pumps

    def get_pump(self, tag_number):
        pump = self._pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}

    def list_pumps(self):
        return {"success": True, "data": list(self._pumps.values())}


class FakeCMONRepository:
    """Shaped to match the REAL condition_monitoring_reading_repository.
    list_all()'s own dict return contract, verified directly against
    production -- see test_fleet_analytics.py's own FakeCMONRepository
    docstring for why a bare-list fake here would mask a real bug."""

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


class FakeWhatsAppRepository:
    """A repository whose create_pending() raises -- the SAME "must never
    persist" proof test_stock_response_standard.py's own fixture already
    establishes, reused here to prove every new fleet-analytics query
    stays read-only all the way through process_inbound_message()."""

    def __init__(self, identity):
        self._identity = identity

    def find_identity_by_sender_hash(self, sender_hash):
        return self._identity

    def find_pending_by_delivery_key(self, provider, provider_message_id, sender_user_id):
        return None

    def find_actionable_pending_list(self, sender_user_id):
        return []

    def create_pending(self, payload):
        raise AssertionError("LTSA AI fleet-analytics query path must never persist a pending row")


def _identity(user_id="u-fleet-ack-test"):
    from API.auth_service import AuthenticatedIdentity

    return AuthenticatedIdentity(
        user_id=user_id, email="u@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role="TAP_ADMIN",
        permissions=frozenset({"maintenance.read"}), data_scope_type=None, data_scope_value=None,
    )


def _pump(tag, area="FRAKSINASI"):
    return {"tag_number": tag, "area": area, "status": "Active"}


def _cmon(tag, reading_date, **fields):
    row = {"asset_code": tag, "reading_date": reading_date, "condition_monitoring_reading_code": f"CMONR-{tag}-{reading_date}"}
    row.update(fields)
    return row


class _AckRecorder:
    def __init__(self):
        self.messages = []

    def __call__(self, text):
        self.messages.append(text)


class _Fixture:
    def __init__(self, pumps, cmon_rows=(), pm_schedules=(), compatibilities=(), seals=(), stock_pools=()):
        self.pump_gateway = FakePumpGateway({p["tag_number"]: p for p in pumps})
        self.cmon_repo = FakeCMONRepository(cmon_rows)
        self.pm_repo = FakePMOccurrenceRepository()
        self.cm_report_repo = FakeListRepository(())
        self.pm_schedule_repo = FakeListRepository(pm_schedules)
        self.compat_gateway = FakeSealPumpCompatibilityGateway(compatibilities)
        self.seal_gateway = FakeSealGateway(seals)
        self.stock_repo = FakeStockRepository(stock_pools)
        self.ack_recorder = _AckRecorder()

    def deps(self):
        return LTSAAIQueryDependencies(
            ai_client=None, maintenance_history_gateway=None, work_order_gateway=None,
            installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
            condition_monitoring_reading_gateway=None, installation_report_repository=None,
            mechanical_seal_stock_repository=self.stock_repo,
            condition_monitoring_reading_repository=self.cmon_repo,
            fleet_executive_summary_service=None,
            pm_occurrence_repository=self.pm_repo, cm_report_repository=self.cm_report_repo,
            pm_schedule_repository=self.pm_schedule_repo,
            seal_pump_compatibility_gateway=self.compat_gateway, seal_gateway=self.seal_gateway,
            send_immediate_ack=self.ack_recorder,
        )

    def send(self, text, *, provider_message_id, repository=None, identity=None):
        repository = repository or FakeWhatsAppRepository(identity or _identity())
        return process_inbound_message(
            provider="whatsapp_cloud", provider_message_id=provider_message_id,
            sender_identifier="+6281111111199", text=text, repository=repository,
            pump_gateway=self.pump_gateway, ltsa_ai_query_deps=self.deps(),
        )


def _temperature_fixture():
    return _Fixture(
        pumps=[_pump("PUMP-A"), _pump("PUMP-B")],
        cmon_rows=[_cmon("PUMP-A", RECENT, suction_temp=176.0), _cmon("PUMP-B", RECENT, suction_temp=90.0)],
    )


# -- Test B: webhook retry cannot duplicate the final answer ------------------


def test_retrying_same_message_id_never_duplicates_the_final_answer():
    _asset_context_cache._entries.clear()
    _fleet_query_delivery_tracker._seen.clear()
    identity = _identity("u-retry-test")
    repository = FakeWhatsAppRepository(identity)
    fixture = _temperature_fixture()

    first = fixture.send(
        "Pompa mana yang temperaturnya paling tinggi?", provider_message_id="MSG-RETRY-1", repository=repository,
    )
    assert first.status == "ANSWERED"
    assert first.reply is not None
    assert "PUMP-A" in first.reply

    retry = fixture.send(
        "Pompa mana yang temperaturnya paling tinggi?", provider_message_id="MSG-RETRY-1", repository=repository,
    )
    assert retry.message == "DUPLICATE_DELIVERY"
    assert retry.reply is None

    # Exactly one acknowledgement + one real answer, never two of either.
    assert fixture.ack_recorder.messages == ["Sedang menganalisis kondisi fleet LTSA..."]


def test_a_genuinely_new_message_id_after_a_retry_still_gets_answered():
    _asset_context_cache._entries.clear()
    _fleet_query_delivery_tracker._seen.clear()
    identity = _identity("u-retry-test-2")
    repository = FakeWhatsAppRepository(identity)
    fixture = _temperature_fixture()

    fixture.send("Pompa mana yang temperaturnya paling tinggi?", provider_message_id="MSG-A", repository=repository)
    fixture.send("Pompa mana yang temperaturnya paling tinggi?", provider_message_id="MSG-A", repository=repository)
    third = fixture.send("Pompa mana yang temperaturnya paling tinggi?", provider_message_id="MSG-B", repository=repository)

    assert third.status == "ANSWERED"
    assert third.reply is not None
    assert third.message != "DUPLICATE_DELIVERY"


# -- Tests C-H: each fleet-analytics query is genuinely READ-ONLY -------------


def test_temperature_fleet_query_is_read_only():
    fixture = _temperature_fixture()
    result = fixture.send("Pompa mana yang temperaturnya paling tinggi?", provider_message_id="C-1")
    assert result.status == "ANSWERED"


def test_vibration_fleet_query_is_read_only():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")], cmon_rows=[_cmon("PUMP-A", RECENT, vertical_vibration_de=8.2)],
    )
    result = fixture.send("Pompa mana yang vibrationnya paling tinggi?", provider_message_id="D-1")
    assert result.status == "ANSWERED"


def test_current_leak_fleet_query_is_read_only():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_rows=[_cmon("PUMP-A", RECENT, mechanical_seal_leak_de=True, finding="Leak")],
    )
    result = fixture.send("Pompa mana yang sealnya bocor sekarang?", provider_message_id="E-1")
    assert result.status == "ANSWERED"


def test_historical_leak_frequency_fleet_query_is_read_only():
    in_window = (TODAY - timedelta(days=100)).isoformat()
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        cmon_rows=[_cmon("PUMP-A", in_window, mechanical_seal_leak_de=True)],
    )
    result = fixture.send("Pompa mana yang paling sering bocor setahun terakhir?", provider_message_id="F-1")
    assert result.status == "ANSWERED"


def test_fleet_stock_semantics_query_is_read_only():
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        compatibilities=[{"pump_tag_number": "PUMP-A", "seal_code": "T48MP"}],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {"stock_pool_id": "P1", "seal_type": "T48MP", "quantity_available": 0, "applications": [{"equipment_tag": "PUMP-A"}]},
        ],
    )
    result = fixture.send("Pompa mana yang stock sealnya 0?", provider_message_id="G-1")
    assert result.status == "ANSWERED"


def test_overdue_pm_fleet_query_is_read_only():
    overdue_due = (TODAY - timedelta(days=10)).isoformat()
    fixture = _Fixture(
        pumps=[_pump("PUMP-A")],
        pm_schedules=[{"asset_code": "PUMP-A", "pm_schedule_code": "S-1", "next_due": overdue_due, "status": "ACTIVE"}],
    )
    result = fixture.send("Pompa mana yang overdue PM?", provider_message_id="H-1")
    assert result.status == "ANSWERED"
    assert "PUMP-A" in (result.reply or "")


# -- Test J: no O(N) gateway regression through the full WhatsApp path -------


def test_fleet_query_through_whatsapp_path_stays_o1_not_per_pump():
    pumps = [_pump(f"PUMP-{i}") for i in range(12)]
    cmon_rows = [_cmon(f"PUMP-{i}", RECENT, suction_temp=50.0 + i) for i in range(12)]
    fixture = _Fixture(
        pumps=pumps,
        cmon_rows=cmon_rows,
        compatibilities=[{"pump_tag_number": f"PUMP-{i}", "seal_code": "T48MP"} for i in range(12)],
        seals=[{"seal_code": "T48MP", "seal_name": "T48MP Seal"}],
        stock_pools=[
            {"stock_pool_id": "P1", "seal_type": "T48MP", "quantity_available": 5,
             "applications": [{"equipment_tag": f"PUMP-{i}"} for i in range(12)]},
        ],
    )
    result = fixture.send("Pompa mana yang temperaturnya paling tinggi?", provider_message_id="J-1")
    assert result.status == "ANSWERED"

    assert fixture.cmon_repo.calls == 1
    assert fixture.pm_repo.calls == 1
    assert fixture.cm_report_repo.calls == 1
    assert fixture.pm_schedule_repo.calls == 1
    assert fixture.compat_gateway.calls == 1
    assert fixture.seal_gateway.calls == 1
    assert fixture.stock_repo.calls == 1
