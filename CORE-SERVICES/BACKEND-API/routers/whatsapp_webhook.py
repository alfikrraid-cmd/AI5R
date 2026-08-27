from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from API.whatsapp_intake_service import process_inbound_message
from dependencies import get_pump_gateway, get_whatsapp_intake_repository

router = APIRouter()

_WEBHOOK_PATH = "/api/ltsa/whatsapp/webhook"


@router.get(_WEBHOOK_PATH)
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if not expected:
        raise HTTPException(status_code=403, detail="WhatsApp webhook verification is not configured")
    if (
        hub_mode != "subscribe"
        or not hub_verify_token
        or hub_challenge is None
        or not hmac.compare_digest(hub_verify_token, expected)
    ):
        raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed")
    return PlainTextResponse(content=hub_challenge, status_code=200)


def _signature_valid(raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = os.getenv("META_APP_SECRET")
    if not app_secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    supplied = signature_header[len("sha256="):]
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


def _handle_inbound_message(message: dict[str, Any], repository, pump_gateway) -> dict[str, Any]:
    provider_message_id = message.get("id")
    sender_identifier = message.get("from")
    if not provider_message_id or not sender_identifier:
        return {"status": "IGNORED_MALFORMED_MESSAGE"}
    text_body = (message.get("text") or {}).get("body") or ""
    result = process_inbound_message(
        provider="whatsapp_cloud",
        provider_message_id=provider_message_id,
        sender_identifier=sender_identifier,
        text=text_body,
        repository=repository,
        pump_gateway=pump_gateway,
        provider_payload=message,
    )
    return {"status": result.status, "message": result.message}


@router.post(_WEBHOOK_PATH)
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    repository=Depends(get_whatsapp_intake_repository),
    pump_gateway=Depends(get_pump_gateway),
) -> dict[str, Any]:
    raw_body = await request.body()
    if not _signature_valid(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid WhatsApp webhook signature")

    try:
        envelope = await request.json()
    except Exception:
        envelope = None

    results: list[dict[str, Any]] = []
    for entry in (envelope or {}).get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            statuses = value.get("statuses") or []
            if messages:
                for message in messages:
                    results.append(_handle_inbound_message(message, repository, pump_gateway))
            elif statuses:
                results.append({"status": "STATUS_ACKNOWLEDGED"})
            else:
                results.append({"status": "UNKNOWN_EVENT_ACKNOWLEDGED"})

    if not results:
        results.append({"status": "UNKNOWN_EVENT_ACKNOWLEDGED"})

    return {"success": True, "results": results}


__all__ = ["router"]
