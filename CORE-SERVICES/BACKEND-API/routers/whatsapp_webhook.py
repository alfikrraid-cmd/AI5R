from __future__ import annotations

import dataclasses
import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from API.whatsapp_intake_service import LTSAAIQueryDependencies, normalize_sender_identifier, process_inbound_message
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
    get_whatsapp_outbound_client,
    get_work_order_gateway,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_WEBHOOK_PATH = "/api/ltsa/whatsapp/webhook"


def _correlation_id(value: str | None) -> str | None:
    # MWO-025J2 Part G -- never log a full provider_message_id (tightens
    # MWO-025G's original choice to log it verbatim as "safe" -- it's
    # still an opaque Meta id, but this MWO's explicit rule is stricter).
    # A truncated hash is stable enough to correlate related log lines
    # without being reversible to the raw id.
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


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


def _send_outbound_reply(
    outbound_client,
    repository,
    recipient: str,
    text: str,
    provider_message_id: str | None,
    intake_id: str | None,
    intake_state: str | None,
) -> None:
    # Safe-by-construction: only ever called with a reply the intake
    # service already decided (never re-derived here), and never logs
    # `recipient` or `text` -- only a truncated correlation id and the
    # transport result, per MWO-025J2's privacy-preserving observability
    # contract.
    try:
        result = outbound_client.send_text(recipient, text)
    except Exception:
        logger.info(
            "event=whatsapp_outbound_result provider_message_id=%s status=FAILED",
            _correlation_id(provider_message_id),
        )
        return
    logger.info(
        "event=whatsapp_outbound_result provider_message_id=%s status=%s http_status=%s",
        _correlation_id(provider_message_id),
        result.status,
        result.http_status,
    )

    # MWO-025J2 Part E -- record Meta's own id for this outbound message
    # against the pending row it answers, so a later inbound reply's
    # context.id can resolve to this exact conversation. Best-effort: a
    # failure here never affects the already-completed send/ack.
    if result.status == "SUCCESS" and result.provider_message_id and intake_id and intake_state:
        try:
            repository.transition_pending(
                intake_id,
                state=intake_state,
                last_outbound_provider_message_id=result.provider_message_id,
            )
        except Exception:
            logger.info(
                "event=whatsapp_outbound_result provider_message_id=%s status=CORRELATION_PERSIST_FAILED",
                _correlation_id(provider_message_id),
            )


def _handle_inbound_message(
    message: dict[str, Any],
    repository,
    pump_gateway,
    outbound_client,
    cmon_repository,
    pm_repository,
    ltsa_ai_query_deps,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    provider_message_id = message.get("id")
    sender_identifier = message.get("from")
    if not provider_message_id or not sender_identifier:
        return {"status": "IGNORED_MALFORMED_MESSAGE"}
    text_body = (message.get("text") or {}).get("body") or ""
    # MWO-025J2 Part E -- Meta sets context.id when the user replies to
    # (quotes) a specific prior message; when present it names the exact
    # AI5R outbound message being answered.
    context_message_id = (message.get("context") or {}).get("id")

    # MWO-LTSA-FLEET-ATTENTION-001 -- bound to THIS message's own
    # recipient (ltsa_ai_query_deps itself is constructed once per
    # request, shared across every message in a batched webhook payload,
    # so the ack target can only be fixed here, per message). Best-effort,
    # synchronous (unlike the final reply, never backgrounded) -- a fleet
    # query's own acknowledgement needs to reach the user BEFORE the slow
    # computation runs, not after the request already returned.
    per_message_deps = ltsa_ai_query_deps
    try:
        ack_recipient = normalize_sender_identifier(sender_identifier)
    except ValueError:
        ack_recipient = None
    if ack_recipient:
        per_message_deps = dataclasses.replace(
            ltsa_ai_query_deps,
            send_immediate_ack=lambda text, _r=ack_recipient: outbound_client.send_text(_r, text),
        )

    result = process_inbound_message(
        provider="whatsapp_cloud",
        provider_message_id=provider_message_id,
        sender_identifier=sender_identifier,
        text=text_body,
        repository=repository,
        pump_gateway=pump_gateway,
        provider_payload=message,
        context_message_id=context_message_id,
        cmon_repository=cmon_repository,
        pm_repository=pm_repository,
        ltsa_ai_query_deps=per_message_deps,
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
            intake = result.intake or {}
            background_tasks.add_task(
                _send_outbound_reply,
                outbound_client,
                repository,
                recipient,
                result.reply,
                provider_message_id,
                intake.get("intake_id"),
                intake.get("state"),
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
) -> dict[str, Any]:
    # Same canonical gateways/services routers/copilot.py's own
    # ask_copilot_endpoint already depends on -- no new gateway, no
    # duplicated business logic, WhatsApp calls the exact same LTSA AI
    # service the dashboard does. ltsa_ai_condition_monitoring_reading_
    # repository/ltsa_ai_pm_occurrence_repository resolve the SAME
    # repository singletons cmon_repository/pm_repository above already
    # use for the CMON/PM WRITE flows (see get_ltsa_ai_condition_
    # monitoring_reading_repository's own docstring for why each is a
    # distinct dependency callable, not a second repository).
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
                        _correlation_id(message.get("id")),
                    )
                    results.append(
                        _handle_inbound_message(
                            message, repository, pump_gateway, outbound_client, cmon_repository, pm_repository,
                            ltsa_ai_query_deps, background_tasks,
                        )
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
