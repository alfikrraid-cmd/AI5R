"""MWO-LTSA-STOCK-RESPONSE-STANDARD-001 -- regression tests for the
generic mechanical seal stock response (canonical tag/model/size/qty,
location when available, installed-seal status, zero-stock vs. no-
compatible-seal distinction, multiple-seal separation) and for the
WhatsApp conversational-context resolution ("cek stock seal yang
tersedia" after "bagaimana kondisi <tag>?").
"""

from API.copilot_ask_service import DATA_GAP, FACT, _detect_intent, ask_copilot
from API.equipment_timeline_service import PumpLifecycleCurrentSeal
from API.whatsapp_intake_service import LTSAAIQueryDependencies, _asset_context_cache, process_inbound_message
from API.whatsapp_intake_service import _normalize_pump_tag_text, hash_sender_identifier, normalize_sender_identifier

TAG = "211-P-13AR"


class FakePumpGateway:
    def __init__(self):
        self.pumps = {TAG: {"tag_number": TAG, "area": "FRAKSINASI", "status": "Active"}}

    def get_pump(self, tag_number):
        pump = self.pumps.get(tag_number)
        return {"success": bool(pump), "data": pump}


class FakeMechanicalSealStockRepository:
    def __init__(self, pools):
        self._pools = pools

    def list_pools(self, limit=200):
        return {"success": True, "data": self._pools}


class FakeEquipmentTimelineService:
    def __init__(self, current_seal=None):
        self._current_seal = current_seal

    def build_current_seal(self, tag_number):
        return self._current_seal


def _pool(seal_type, qty, nominal_size="60", size_unit="mm", location=None, tag=TAG, pool_id=None):
    return {
        "stock_pool_id": pool_id or f"POOL-{seal_type}",
        "seal_type": seal_type,
        "quantity_available": qty,
        "nominal_size": nominal_size,
        "size_unit": size_unit,
        "stock_location": location,
        "applications": [{"equipment_tag": tag}],
    }


def _ask(mechanical_seal_stock_repository, equipment_timeline_service=None, language="id", tag=TAG):
    return ask_copilot(
        f"Ada stock seal untuk {tag}?", tag, None,
        pump_gateway=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None,
        equipment_timeline_service=equipment_timeline_service or FakeEquipmentTimelineService(),
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None, cm_report_repository=None,
        language=language,
    )


# -- STOCK_TAG_NORMALIZATION --------------------------------------------------


def test_stock_tag_normalization_resolves_variant_spelling():
    for text in ("Ada stock seal untuk 211p13ar?", "Stock seal 211-P-13AR", "Cek seal tersedia untuk 211p13ar",
                 "Spare seal 211p13ar", "Berapa stock mechanical seal 211p13ar?"):
        assert _normalize_pump_tag_text(text) == TAG


# -- STOCK_MODEL / STOCK_SIZE / STOCK_QTY -------------------------------------


def test_stock_model_size_and_quantity_are_all_shown():
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 4, nominal_size="60", size_unit="mm")])
    answer = _ask(repo)
    assert answer.kind == FACT
    assert "T6014DP" in answer.answer
    assert "60 mm" in answer.answer
    assert "4 unit" in answer.answer
    assert TAG in answer.answer


def test_stock_size_uses_canonical_structured_field_not_parsed_from_identifier():
    # Identifier string deliberately contains a DIFFERENT size than the
    # canonical structured field -- proves the field, not string parsing,
    # is the source.
    repo = FakeMechanicalSealStockRepository(
        [_pool("LTSA-SEAL-T6014DP-99MM", 4, nominal_size="60", size_unit="mm")]
    )
    answer = _ask(repo)
    assert "60 mm" in answer.answer
    assert "99" not in answer.answer or "99MM" in answer.answer  # only inside the model name itself, never as Size


# -- STOCK_ZERO ----------------------------------------------------------------


def test_stock_zero_shows_zero_not_no_compatible_seal():
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 0)])
    answer = _ask(repo)
    assert answer.kind == FACT
    assert "0 unit" in answer.answer
    assert "tidak ada seal compatible" not in answer.answer.lower()


# -- STOCK_MULTIPLE --------------------------------------------------------------


def test_stock_multiple_seals_kept_separate_never_combined():
    repo = FakeMechanicalSealStockRepository(
        [
            _pool("T6014DP", 4, nominal_size="60", size_unit="mm", pool_id="POOL-1"),
            _pool("T48MP", 2, nominal_size="48", size_unit="mm", pool_id="POOL-2"),
        ]
    )
    answer = _ask(repo)
    assert "T6014DP" in answer.answer
    assert "T48MP" in answer.answer
    assert "60 mm" in answer.answer
    assert "48 mm" in answer.answer
    assert "4 unit" in answer.answer
    assert "2 unit" in answer.answer
    # never summed into a single combined quantity
    assert "6 unit" not in answer.answer


# -- STOCK_INSTALLED_UNKNOWN ---------------------------------------------------


def test_stock_never_claims_compatible_seal_is_installed_when_unconfirmed():
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 4)])
    answer = _ask(repo, equipment_timeline_service=FakeEquipmentTimelineService(current_seal=None))
    assert "Belum terkonfirmasi" in answer.answer


def test_stock_shows_confirmed_installed_seal_when_present():
    current_seal = PumpLifecycleCurrentSeal(
        seal_code="T6014DP", seal_name="Mechanical Seal", manufacturer=None, model=None,
        shaft_size=None, material=None, temperature_limit=None, pressure_limit=None,
        status=None, installation_code="INST-1", installed_at="2026-08-01", source="InstallationReportRepository",
    )
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 4)])
    answer = _ask(repo, equipment_timeline_service=FakeEquipmentTimelineService(current_seal=current_seal))
    assert "terkonfirmasi" in answer.answer
    assert "Belum terkonfirmasi" not in answer.answer


# -- STOCK_SIZE_MISSING ---------------------------------------------------------


def test_stock_size_missing_renders_n_a_never_omitted():
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 4, nominal_size=None, size_unit=None)])
    answer = _ask(repo)
    assert "Size: N/A" in answer.answer


def test_stock_size_missing_unit_shows_bare_nominal_size():
    repo = FakeMechanicalSealStockRepository([_pool("T6014DP", 4, nominal_size="60", size_unit=None)])
    answer = _ask(repo)
    assert "Size: 60" in answer.answer


# -- Zero-stock never reported as unavailable/DATA_GAP -------------------------


def test_stock_data_unavailable_is_data_gap_not_fabricated():
    class _FailingRepository:
        def list_pools(self, limit=200):
            return {"success": False}

    answer = _ask(_FailingRepository())
    assert answer.kind == DATA_GAP


# -- STOCK_CONTEXT / STOCK_CONTEXT_OVERRIDE / STOCK_NO_CONTEXT (WhatsApp layer) --


class FakeWhatsAppRepository:
    def __init__(self, identity):
        self._identity = identity

    def find_identity_by_sender_hash(self, sender_hash):
        return self._identity

    def find_pending_by_delivery_key(self, provider, provider_message_id, sender_user_id):
        return None

    def find_actionable_pending_list(self, sender_user_id):
        return []

    def create_pending(self, payload):
        raise AssertionError("LTSA AI query path must never persist a pending row")


def _identity(user_id="u-stock-context"):
    from API.auth_service import AuthenticatedIdentity
    return AuthenticatedIdentity(
        user_id=user_id, email="u@example.test", organization_id="org-1",
        organization_code="PERTAMINA_RU_II", role="TAP_ADMIN",
        permissions=frozenset({"maintenance.read"}), data_scope_type=None, data_scope_value=None,
    )


def _query_deps(mechanical_seal_stock_repository):
    return LTSAAIQueryDependencies(
        ai_client=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None,
        equipment_timeline_service=FakeEquipmentTimelineService(),
        condition_monitoring_reading_gateway=None, installation_report_repository=None,
        mechanical_seal_stock_repository=mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=None, fleet_executive_summary_service=None,
        pm_occurrence_repository=None, cm_report_repository=None,
    )


def test_stock_context_follow_up_inherits_valid_equipment_context():
    _asset_context_cache._entries.clear()
    identity = _identity()
    repository = FakeWhatsAppRepository(identity)
    pump_gateway = FakePumpGateway()
    stock_repository = FakeMechanicalSealStockRepository([_pool("T6014DP", 4)])
    deps = _query_deps(stock_repository)

    first = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-1", sender_identifier="+6281111111111",
        text=f"Bagaimana kondisi {TAG}?", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert first.status == "ANSWERED"

    second = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-2", sender_identifier="+6281111111111",
        text="Cek stock seal yang tersedia", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert second.status == "ANSWERED"
    assert TAG in second.reply
    assert "T6014DP" in second.reply


# -- SENDER-IDENTITY-INDEPENDENT CANONICAL FACTS ------------------------------
#
# "Same canonical equipment + same semantic intent + same authorized scope
# => same factual answer." Sender identity may ALLOW/DENY access (a gate),
# never select a different intent, tag, or retrieval path.


def test_all_stock_paraphrases_detect_the_same_inventory_intent_and_tag():
    equipment_tag = "211-P-10A"
    for text in (
        "Ada stock seal 211p10a?",
        "Stock 211p10a ada?",
        "Stok seal 211-p-10a berapa?",
        "Seal 211P10A ready?",
        "Ada spare seal untuk 211p10a?",
    ):
        assert _detect_intent(text) == "inventory"
        assert _normalize_pump_tag_text(text) == equipment_tag


def test_two_senders_with_equivalent_scope_get_identical_canonical_facts():
    # TAP_ENGINEER and JOHN_CRANE_ENGINEER are both unrestricted
    # (_UNRESTRICTED_ROLES) -- "Semua area" for both, an equivalent READ
    # scope even though they are different roles/organizations/users.
    from API.auth_service import AuthenticatedIdentity

    identity_a = AuthenticatedIdentity(
        user_id="sender-a", email="a@tap.internal", organization_id="org-tap",
        organization_code="TAP", role="TAP_ENGINEER",
        permissions=frozenset({"maintenance.read"}), data_scope_type=None, data_scope_value=None,
    )
    identity_b = AuthenticatedIdentity(
        user_id="sender-b", email="b@tap.internal", organization_id="org-tap",
        organization_code="TAP", role="JOHN_CRANE_ENGINEER",
        permissions=frozenset({"maintenance.read"}), data_scope_type=None, data_scope_value=None,
    )
    phone_a, phone_b = "+6281111111111", "+6282222222222"

    class FakeMultiSenderRepository:
        def __init__(self, identities_by_phone):
            self._by_hash = {
                hash_sender_identifier(normalize_sender_identifier(phone)): identity
                for phone, identity in identities_by_phone.items()
            }

        def find_identity_by_sender_hash(self, sender_hash):
            return self._by_hash.get(sender_hash)

        def find_pending_by_delivery_key(self, provider, provider_message_id, sender_user_id):
            return None

        def find_actionable_pending_list(self, sender_user_id):
            return []

    repository = FakeMultiSenderRepository({phone_a: identity_a, phone_b: identity_b})
    pump_gateway = FakePumpGateway()
    stock_repository = FakeMechanicalSealStockRepository([_pool("T6014DP", 4)])
    deps = _query_deps(stock_repository)

    result_a = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-A", sender_identifier=phone_a,
        text=f"Ada stock seal untuk {TAG}?", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    result_b = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-B", sender_identifier=phone_b,
        text=f"Stock {TAG} ada?", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )

    assert result_a.status == "ANSWERED"
    assert result_b.status == "ANSWERED"
    assert result_a.reply == result_b.reply
    assert "T6014DP" in result_a.reply


def test_stock_context_override_explicit_new_equipment_wins():
    _asset_context_cache._entries.clear()
    identity = _identity()
    repository = FakeWhatsAppRepository(identity)
    pump_gateway = FakePumpGateway()
    pump_gateway.pumps["210-P-05AR"] = {"tag_number": "210-P-05AR", "area": "FRAKSINASI", "status": "Active"}
    stock_repository = FakeMechanicalSealStockRepository(
        [_pool("T6014DP", 4, tag=TAG), _pool("T48MP", 2, tag="210-P-05AR", pool_id="POOL-OTHER")]
    )
    deps = _query_deps(stock_repository)

    first = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-3", sender_identifier="+6281111111112",
        text=f"Bagaimana kondisi {TAG}?", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert first.status == "ANSWERED"

    # Explicit equipment in THIS message overrides the earlier context.
    second = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-4", sender_identifier="+6281111111112",
        text="Stock seal 210-P-05AR", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert "210-P-05AR" in second.reply
    assert "T48MP" in second.reply


def test_stock_no_context_asks_which_pump_never_silently_fails():
    _asset_context_cache._entries.clear()
    identity = _identity(user_id="u-no-context")
    repository = FakeWhatsAppRepository(identity)
    pump_gateway = FakePumpGateway()
    stock_repository = FakeMechanicalSealStockRepository([_pool("T6014DP", 4)])
    deps = _query_deps(stock_repository)

    result = process_inbound_message(
        provider="whatsapp_cloud", provider_message_id="MSG-5", sender_identifier="+6281111111113",
        text="Cek stock seal yang tersedia", repository=repository, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert result.status == "ANSWERED"
    assert result.reply == "Stock seal untuk pompa mana?"
