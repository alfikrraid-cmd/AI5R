from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from API.whatsapp_intake_service import normalize_sender_identifier, process_inbound_message
from dependencies import get_pump_gateway, get_whatsapp_intake_repository, get_whatsapp_outbound_client

logger = logging.getLogger(__name__)

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


def _send_outbound_reply(outbound_client, recipient: str, text: str, provider_message_id: str | None) -> None:
    # Safe-by-construction: only ever called with a reply the intake
    # service already decided (never re-derived here), and never logs
    # `recipient` or `text` -- only the provider-assigned message id and
    # the transport result, matching MWO-025G's privacy-preserving
    # observability contract.
    try:
        result = outbound_client.send_text(recipient, text)
    except Exception:
        logger.info(
            "event=whatsapp_outbound_result provider_message_id=%s status=FAILED",
            provider_message_id,
        )
        return
    logger.info(
        "event=whatsapp_outbound_result provider_message_id=%s status=%s http_status=%s",
        provider_message_id,
        result.status,
        result.http_status,
    )


def _handle_inbound_message(
    message: dict[str, Any],
    repository,
    pump_gateway,
    outbound_client,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
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

    # A duplicate webhook delivery of the same provider_message_id must not
    # produce a duplicate WhatsApp reply (MWO-025G Phase 5) -- reuses the
    # existing DUPLICATE_DELIVERY signal _persist() already produces
    # (whatsapp_intake_service.py), not a new idempotency mechanism.
    if result.reply and result.message != "DUPLICATE_DELIVERY":
        try:
            recipient = normalize_sender_identifier(sender_identifier)
        except ValueError:
            recipient = None
        if recipient:
            background_tasks.add_task(
                _send_outbound_reply, outbound_client, recipient, result.reply, provider_message_id
            )

    return {"status": result.status, "message": result.message}


@router.post(_WEBHOOK_PATH)
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    repository=Depends(get_whatsapp_intake_repository),
    pump_gateway=Depends(get_pump_gateway),
    outbound_client=Depends(get_whatsapp_outbound_client),
) -> dict[str, Any]:
    raw_body = await request.body()
    if not _signature_valid(raw_body, x_hub_signature_256):
        logger.info("event=whatsapp_webhook_received event_type=unknown signature_valid=false")
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
                    logger.info(
                        "event=whatsapp_webhook_received event_type=messages provider_message_id=%s signature_valid=true",
                        message.get("id"),
                    )
                    results.append(
                        _handle_inbound_message(message, repository, pump_gateway, outbound_client, background_tasks)
                    )
            elif statuses:
                logger.info("event=whatsapp_webhook_received event_type=statuses signature_valid=true")
                results.append({"status": "STATUS_ACKNOWLEDGED"})
            else:
                logger.info("event=whatsapp_webhook_received event_type=unsupported signature_valid=true")
                results.append({"status": "UNKNOWN_EVENT_ACKNOWLEDGED"})

    if not results:
        results.append({"status": "UNKNOWN_EVENT_ACKNOWLEDGED"})

    return {"success": True, "results": results}


__all__ = ["router"]
