"""
MWO-LTSA-TAP-GROUP-AGENT-001 -- internal ingress endpoint for the TAP LTSA
WhatsApp Group Agent transport (a separate Node.js/Baileys process, never
this FastAPI app itself). Mirrors whatsapp_intake.py's own
"internal, ingress-secret-gated" boundary pattern exactly, but with its
OWN, distinct secret (AI5R_WHATSAPP_GROUP_INGRESS_SECRET) -- this
boundary's authorization is never shared with or repurposed from the
personal WhatsApp intake/webhook boundaries, matching the same discipline
main.py's own comment already documents for keeping those two separate
from each other.

Router-only: no business logic, no LTSA reasoning here. Tag extraction is
imported (not duplicated) from routers.copilot, and orchestrate_copilot()
is the exact same function that router's own /api/ltsa/copilot/ask
endpoint calls -- this endpoint is a second, group-authorized caller of
that one shared engine, not a new one.

whatsapp_webhook.py, whatsapp_intake.py, whatsapp_intake_service.py, and
whatsapp_outbound_client.py are never imported or modified here -- the
personal WhatsApp flow is completely unaffected by this file's existence.
"""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from API.copilot_orchestrator import orchestrate_copilot
from API.whatsapp_group_agent_service import GroupMessageEvent, process_group_message
from dependencies import (
    get_cm_report_repository,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_copilot_ai_client,
    get_equipment_timeline_service,
    get_equipment_360_service,
    get_fleet_executive_summary_service,
    get_group_authorization_repository,
    get_group_message_rate_limiter,
    get_installation_gateway,
    get_installation_report_repository,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_mechanical_seal_stock_repository,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_repository,
    get_pm_schedule_repository,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_leak_diagnostic_service,
    get_seal_pump_compatibility_gateway,
    get_whatsapp_intake_repository,
    get_work_order_gateway,
)
from routers.copilot import _extract_pump_tag_candidates, _normalize_pump_tag, _require_tag_in_scope

router = APIRouter()


class WhatsAppGroupMessageRequest(BaseModel):
    group_id: str
    sender_identifier: str
    provider_message_id: str
    text: str
    is_from_self: bool = False


class WhatsAppGroupMessageResponse(BaseModel):
    status: str
    reply: str | None = None
    ack: str | None = None


def _require_group_ingress_secret(x_ai5r_whatsapp_group_ingress_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("AI5R_WHATSAPP_GROUP_INGRESS_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="WhatsApp group agent is not configured")
    if not x_ai5r_whatsapp_group_ingress_secret or not hmac.compare_digest(
        x_ai5r_whatsapp_group_ingress_secret, expected
    ):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp group ingress secret")


@router.post(
    "/api/ltsa/whatsapp-group/message",
    dependencies=[Depends(_require_group_ingress_secret)],
)
def receive_whatsapp_group_message(
    payload: WhatsAppGroupMessageRequest,
    group_repository=Depends(get_group_authorization_repository),
    sender_identity_repository=Depends(get_whatsapp_intake_repository),
    rate_limiter=Depends(get_group_message_rate_limiter),
    pump_gateway=Depends(get_pump_gateway),
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    installation_gateway=Depends(get_installation_gateway),
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    equipment_360_service=Depends(get_equipment_360_service),
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    installation_report_repository=Depends(get_installation_report_repository),
    mechanical_seal_stock_repository=Depends(get_mechanical_seal_stock_repository),
    seal_leak_diagnostic_service=Depends(get_seal_leak_diagnostic_service),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    fleet_executive_summary_service=Depends(get_fleet_executive_summary_service),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
    cm_report_repository=Depends(get_cm_report_repository),
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    seal_gateway=Depends(get_seal_gateway),
    ai_client=Depends(get_copilot_ai_client),
) -> WhatsAppGroupMessageResponse:
    def _ask_ltsa_question(question: str, effective_scope: "frozenset[str] | None") -> str:
        # Identical shape to routers/copilot.py's ask_copilot_endpoint:
        # explicit tag wins, else extract from text (reject >1 candidate
        # the same "ask again" way), else fleet-wide (tag=None) --
        # orchestrate_copilot() itself decides how to answer a tag-less
        # question, exactly as it already does for the dashboard.
        candidates = _extract_pump_tag_candidates(question)
        tag: str | None = None
        if len(candidates) > 1:
            return (
                "Saya menemukan beberapa tag pompa di pertanyaan itu. "
                "Sebutkan satu tag pompa saja dan tanyakan lagi."
            )
        if candidates:
            tag = _normalize_pump_tag(candidates[0]) or candidates[0]
            _require_tag_in_scope(tag, pump_gateway, effective_scope)
        answer, _tools_used = orchestrate_copilot(
            question,
            tag,
            effective_scope,
            ai_client,
            pump_gateway=pump_gateway,
            maintenance_history_gateway=maintenance_history_gateway,
            work_order_gateway=work_order_gateway,
            installation_gateway=installation_gateway,
            ltsa_knowledge_service=ltsa_knowledge_service,
            equipment_timeline_service=equipment_timeline_service,
            equipment_360_service=equipment_360_service,
            condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
            installation_report_repository=installation_report_repository,
            mechanical_seal_stock_repository=mechanical_seal_stock_repository,
            seal_leak_diagnostic_service=seal_leak_diagnostic_service,
            condition_monitoring_reading_repository=condition_monitoring_reading_repository,
            fleet_executive_summary_service=fleet_executive_summary_service,
            pm_occurrence_repository=pm_occurrence_repository,
            cm_report_repository=cm_report_repository,
            pm_cm_evidence_repository=pm_cm_evidence_repository,
            pm_schedule_repository=pm_schedule_repository,
            seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
            seal_gateway=seal_gateway,
        )
        return answer.answer

    event = GroupMessageEvent(
        group_id=payload.group_id,
        sender_identifier=payload.sender_identifier,
        provider_message_id=payload.provider_message_id,
        text=payload.text,
        is_from_self=payload.is_from_self,
        is_group_message=True,
    )
    result = process_group_message(
        event,
        group_repository=group_repository,
        sender_identity_repository=sender_identity_repository,
        rate_limiter=rate_limiter,
        ask_ltsa_question=_ask_ltsa_question,
    )
    return WhatsAppGroupMessageResponse(status=result.status, reply=result.reply, ack=result.ack)


__all__ = ["router"]
