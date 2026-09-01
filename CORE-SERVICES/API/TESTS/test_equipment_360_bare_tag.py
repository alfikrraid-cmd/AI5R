from types import SimpleNamespace

from API.auth_service import AuthenticatedIdentity
from API.copilot_ask_service import FACT, ask_copilot
from API.whatsapp_intake_service import LTSAAIQueryDependencies, _handle_ltsa_ai_query
from routers.copilot import _extract_pump_tag_candidates


TAGS = (
    "211P10A",
    "211p10a",
    "211-P-10A",
    "211 p 10 a",
    "211-P-13AR",
    "211p13ar",
)


def _equipment(tag):
    return SimpleNamespace(
        equipment_tag=tag,
        status="RUNNING",
        area="HSC",
        location="TEST",
        pm_latest=None,
        cm_latest=None,
        cmon_latest=None,
        current_seal=None,
        compatible_seals=(),
        seal_stock=(),
        data_gaps=(),
    )


def _ask(question, tag, service):
    return ask_copilot(
        question,
        tag,
        None,
        pump_gateway=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None,
        condition_monitoring_reading_repository=None,
        installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None,
        cm_report_repository=None,
        equipment_360_service=service,
    )


def test_all_valid_bare_tag_forms_use_the_existing_equipment_360_service():
    calls = []

    def service(tag):
        calls.append(tag)
        return _equipment(tag)

    for question in TAGS:
        tag = _extract_pump_tag_candidates(question)[0]
        answer = _ask(question, tag, service)
        assert answer.kind == FACT
        assert answer.answer.startswith("Equipment 360: ")
        assert tag in answer.answer

    assert calls == ["211-P-10A"] * 4 + ["211-P-13AR"] * 2


def test_partial_bare_tag_is_never_guessed_to_a_full_equipment():
    for question in ("211p10", "211-P-10", "211 p 10"):
        assert _extract_pump_tag_candidates(question) == ()


def test_whatsapp_bare_tag_reaches_the_same_canonical_read_path():
    class PumpGateway:
        def get_pump(self, tag):
            return {"success": True, "data": {"tag_number": tag, "area": "HSC"}}

    identity = AuthenticatedIdentity(
        user_id="bare-tag-reader",
        email="reader@example.test",
        organization_id="org-test",
        organization_code="TEST",
        role="TAP_ENGINEER",
        permissions=frozenset({"maintenance.read"}),
        data_scope_type=None,
        data_scope_value=None,
    )
    calls = []

    def service(tag):
        calls.append(tag)
        return _equipment(tag)

    deps = SimpleNamespace(
        ai_client=None,
        maintenance_history_gateway=None,
        work_order_gateway=None,
        installation_gateway=None,
        ltsa_knowledge_service=None,
        equipment_timeline_service=None,
        condition_monitoring_reading_gateway=None,
        installation_report_repository=None,
        mechanical_seal_stock_repository=None,
        condition_monitoring_reading_repository=None,
        fleet_executive_summary_service=None,
        pm_occurrence_repository=None,
        cm_report_repository=None,
        pm_cm_evidence_repository=None,
        pm_schedule_repository=None,
        seal_pump_compatibility_gateway=None,
        seal_gateway=None,
        equipment_360_service=service,
    )

    result = _handle_ltsa_ai_query("211 p 10 a", identity, PumpGateway(), deps)

    assert result.status == "ANSWERED"
    assert "Equipment 360: 211-P-10A" in result.reply
    assert calls == ["211-P-10A"]
