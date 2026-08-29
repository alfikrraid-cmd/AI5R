from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException

from API.whatsapp_intake_service import process_inbound_message
from dependencies import (
    get_condition_monitoring_reading_repository,
    get_pm_occurrence_repository,
    get_pump_gateway,
    get_whatsapp_intake_repository,
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
) -> Payload:
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
    )
    return {
        "success": result.status not in {"REJECTED"},
        "status": result.status,
        "message": result.message,
        "reply": result.reply,
        "data": _public_intake(result.intake),
    }


__all__ = ["router"]
