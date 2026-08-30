from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException

from API.whatsapp_intake_service import LTSAAIQueryDependencies, process_inbound_message
from dependencies import (
    get_cm_report_repository,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_copilot_ai_client,
    get_equipment_timeline_service,
    get_fleet_executive_summary_service,
    get_installation_gateway,
    get_installation_report_repository,
    get_ltsa_ai_condition_monitoring_reading_repository,
    get_ltsa_ai_pm_occurrence_repository,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_mechanical_seal_stock_repository,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_whatsapp_intake_repository,
    get_work_order_gateway,
)
from models.requests import WhatsAppIntakeRequest
from models.responses import Payload


def _public_intake(row):
    if not isinstance(row, dict):
        return row
    allowed = {
        "intake_id", "provider", "provider_message_id", "sender_user_id", "received_at",
        "detected_domain", "structured_payload", "validation_result", "state",
        "normalized_payload_hash", "confirmation_id", "confirmed_by", "confirmed_at",
        "created_at", "updated_at",
    }
    return {key: value for key, value in row.items() if key in allowed}
router = APIRouter()


def _require_ingress_secret(x_ai5r_whatsapp_ingress_secret: str | None = Header(default=None)) -> None:
    expected = os.getenv("AI5R_WHATSAPP_INGRESS_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="WhatsApp intake is not configured")
    if not x_ai5r_whatsapp_ingress_secret or not hmac.compare_digest(
        x_ai5r_whatsapp_ingress_secret, expected
    ):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp ingress secret")


@router.post("/api/ltsa/whatsapp/intake", dependencies=[Depends(_require_ingress_secret)])
def receive_whatsapp_intake(
    payload: WhatsAppIntakeRequest,
    repository=Depends(get_whatsapp_intake_repository),
    pump_gateway=Depends(get_pump_gateway),
    cmon_repository=Depends(get_condition_monitoring_reading_repository),
    pm_repository=Depends(get_pm_occurrence_repository),
    ai_client=Depends(get_copilot_ai_client),
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    installation_gateway=Depends(get_installation_gateway),
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    installation_report_repository=Depends(get_installation_report_repository),
    mechanical_seal_stock_repository=Depends(get_mechanical_seal_stock_repository),
    ltsa_ai_condition_monitoring_reading_repository=Depends(get_ltsa_ai_condition_monitoring_reading_repository),
    fleet_executive_summary_service=Depends(get_fleet_executive_summary_service),
    ltsa_ai_pm_occurrence_repository=Depends(get_ltsa_ai_pm_occurrence_repository),
    cm_report_repository=Depends(get_cm_report_repository),
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
) -> Payload:
    # ltsa_ai_condition_monitoring_reading_repository/ltsa_ai_pm_
    # occurrence_repository resolve the SAME repository singletons
    # cmon_repository/pm_repository above already use for the CMON/PM
    # WRITE flows (see get_ltsa_ai_condition_monitoring_reading_
    # repository's own docstring for why each is a distinct dependency
    # callable, not a second repository).
    ltsa_ai_query_deps = LTSAAIQueryDependencies(
        ai_client=ai_client,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        installation_gateway=installation_gateway,
        ltsa_knowledge_service=ltsa_knowledge_service,
        equipment_timeline_service=equipment_timeline_service,
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        installation_report_repository=installation_report_repository,
        mechanical_seal_stock_repository=mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=ltsa_ai_condition_monitoring_reading_repository,
        fleet_executive_summary_service=fleet_executive_summary_service,
        pm_occurrence_repository=ltsa_ai_pm_occurrence_repository,
        cm_report_repository=cm_report_repository,
        pm_cm_evidence_repository=pm_cm_evidence_repository,
    )
    result = process_inbound_message(
        provider=payload.provider,
        provider_message_id=payload.provider_message_id,
        sender_identifier=payload.sender_identifier,
        text=payload.text,
        received_at=payload.received_at,
        provider_payload=payload.provider_payload,
        repository=repository,
        pump_gateway=pump_gateway,
        cmon_repository=cmon_repository,
        pm_repository=pm_repository,
        ltsa_ai_query_deps=ltsa_ai_query_deps,
    )
    return {
        "success": result.status not in {"REJECTED"},
        "status": result.status,
        "message": result.message,
        "reply": result.reply,
        "data": _public_intake(result.intake),
    }


__all__ = ["router"]
