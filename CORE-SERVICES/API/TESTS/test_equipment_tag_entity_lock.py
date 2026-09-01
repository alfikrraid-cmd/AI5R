import sys
from pathlib import Path

import pytest
from types import SimpleNamespace

CORE_SERVICES = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES))

from API.auth_service import AuthenticatedIdentity
from API.copilot_ask_service import DATA_GAP, FACT, _detect_intent, ask_copilot
from routers.copilot import _extract_pump_tag_candidates
from API.whatsapp_intake_service import LTSAAIQueryDependencies, process_inbound_message


TAG = "110-P-12B"

def _canonical_tag(raw):
    candidates = _extract_pump_tag_candidates(raw)
    assert len(candidates) == 1
    return candidates[0]


@pytest.mark.parametrize(
    "raw",
    ["110p12b", "110P12B", "110-P-12B", "110 p 12 b", "110-p12b", "110p-12b"],
)
def test_all_110p12b_spellings_normalize_exactly(raw):
    assert _canonical_tag(raw) == TAG


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Kondisi 110p12b", "pump_status"),
        ("CMON terakhir 110p12b", "condition_monitoring"),
        ("CMON 110p12b setahun terakhir", "condition_monitoring"),
        ("Temperature 110p12b terakhir", "condition_monitoring"),
        ("Temperature 110p12b setahun terakhir", "condition_monitoring"),
        ("Vibration 110p12b terakhir", "condition_monitoring"),
        ("Ada stock seal 110p12b", "inventory"),
        ("Compatible seal 110p12b", "seal_compat"),
    ],
)
def test_each_single_equipment_read_keeps_the_exact_current_entity(question, intent):
    assert _canonical_tag(question) == TAG
    assert _detect_intent(question, tag=TAG) == intent


@pytest.mark.parametrize("raw", ["211p10", "211-P-10", "211 p 10"])
def test_partial_tag_is_not_substituted_with_a_suffixed_equipment(raw):
    assert _extract_pump_tag_candidates(raw) == ()


class _CMONRepository:
    def __init__(self):
        self.calls = []

    def list_by_asset(self, tag):
        self.calls.append(tag)
        return [{"reading_date": "2026-08-30", "finding": "bearing stable"}]


class _FleetGatewayMustNotRun:
    def list_condition_monitoring_readings(self):
        raise AssertionError("single-equipment CMON must not use fleet ranking")


def _ask_deps(cmon_repo):
    return dict(
        pump_gateway=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FleetGatewayMustNotRun(),
        installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=cmon_repo,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None,
        cm_report_repository=None,
    )


def test_explicit_cmon_tag_is_locked_before_fleet_dispatch():
    repo = _CMONRepository()
    answer = ask_copilot("Cmon terakhir 110p12b", TAG, None, **_ask_deps(repo), language="id")
    assert answer.kind == FACT
    assert repo.calls == [TAG]
    assert TAG in answer.answer


class _Equipment360Service:
    def __init__(self):
        self.calls = []

    def __call__(self, tag, **_deps):
        self.calls.append(tag)
        return SimpleNamespace(
            equipment_tag=tag, status="Active", area="FRAKSINASI", location="Unit 2", cmon_latest=None,
            pm_latest=None, cm_latest=None, compatible_seals=(), seal_stock=(),
            current_seal=None, data_gaps=("current_seal",),
        )


@pytest.mark.parametrize("raw", ["211P10A", "211p10a", "211-P-10A", "211 p 10 a", "211-P-13AR", "211p13ar"])
def test_bare_exact_tag_routes_to_canonical_equipment_360(raw):
    service = _Equipment360Service()
    deps = _ask_deps(_CMONRepository())
    deps.update(pump_gateway=_PumpGateway(), equipment_360_service=service)
    answer = ask_copilot(raw, _canonical_tag(raw), None, **deps)
    assert answer.kind == FACT
    assert service.calls == [_canonical_tag(raw)]
    assert "Equipment 360" in answer.answer


@pytest.mark.parametrize("raw", ["211p10", "211-P-10", "211 p 10"])
def test_bare_partial_tag_is_controlled_not_found(raw):
    assert _extract_pump_tag_candidates(raw) == ()


class _PumpGateway:
    def get_pump(self, tag):
        if tag in {TAG, "211-P-10A", "211-P-13AR"}:
            return {"success": True, "data": {"tag_number": tag, "area": "FRAKSINASI"}}
        return {"success": False, "data": None}


class _IdentityRepository:
    def __init__(self):
        self.identity = AuthenticatedIdentity(
            user_id="u1", email="u@example.test", organization_id="org1",
            organization_code="ORG", role="TAP_ADMIN",
            permissions=frozenset({"maintenance.read"}), data_scope_type=None, data_scope_value=None,
        )

    def find_identity_by_sender_hash(self, _sender_hash):
        return self.identity

    def find_pending_by_delivery_key(self, *_args):
        return None

    def find_actionable_pending_list(self, _user_id):
        return []


def test_whatsapp_current_message_entity_overrides_previous_context():
    repo = _IdentityRepository()
    pump_gateway = _PumpGateway()
    cmon = _CMONRepository()
    deps = LTSAAIQueryDependencies(
        ai_client=None, maintenance_history_gateway=None, work_order_gateway=None,
        installation_gateway=None, ltsa_knowledge_service=None, equipment_timeline_service=None,
        condition_monitoring_reading_gateway=_FleetGatewayMustNotRun(), installation_report_repository=None,
        mechanical_seal_stock_repository=None, condition_monitoring_reading_repository=cmon,
        fleet_executive_summary_service=None, pm_occurrence_repository=None, cm_report_repository=None,
    )
    first = process_inbound_message(
        provider="test", provider_message_id="m1", sender_identifier="+6281111111111",
        text="Kondisi 211p10a", repository=repo, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert first.status == "ANSWERED"
    second = process_inbound_message(
        provider="test", provider_message_id="m2", sender_identifier="+6281111111111",
        text="Cmon terakhir 110p12b", repository=repo, pump_gateway=pump_gateway,
        ltsa_ai_query_deps=deps,
    )
    assert second.status == "ANSWERED"
    assert cmon.calls == [TAG]
    assert TAG in second.reply
