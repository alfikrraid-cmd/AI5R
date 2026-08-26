from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from API.auth_service import AuthenticatedIdentity
from API.engineering_insight import build_engineering_insight
from dependencies import (
    get_current_user,
    get_engineering_context_engine,
    get_ltsa_knowledge_service,
    get_pump_gateway,
    require_permission,
)
from models.responses import Payload
from routers.pumps import _guard_tag_in_scope

# MWO-LTSA-ENGINEERING-AI-ASSET360-NOT-FOUND-020 -- root cause: the
# frontend (Pump.jsx's postEngineeringAI(), AI5R-STUDIO/dashboard/src/api/
# ai5rClient.js) has called POST /api/ltsa/engineering-ai since the
# engineering-ai/ component family (EngineeringAIStatus/Summary/Findings/
# Evidence/Recommendation/...) was built, but no router for this path was
# ever committed to this branch -- confirmed by repository-wide search
# (git log --all on the exact path returns nothing) and by main.py's own
# comment, which names "routers/engineering_ai.py" as a file that in fact
# does not exist here. Every request 404s at the FastAPI routing layer
# itself (no route matches), which the frontend's .catch() renders as
# "Error" / "Reason: Not Found" -- for every pump, not just 140-P-10B.
# This is Category A (endpoint 404), not a data gap.
#
# Fix is additive only: this router, reusing the EXACT already-deployed,
# already-tested deterministic pipeline routers/pumps.py's own GET
# .../knowledge endpoint already uses for its own `ai_insight` field --
# LTSAKnowledgeService.build(tag) + EngineeringContextEngine.build(tag) +
# build_engineering_insight() (MWO-LTSA-035, rule-free field selection, no
# LLM, no network, no prompt) -- mapped onto the EngineeringAIResponse
# shape the frontend's engineering-ai/ components already expect (their
# own field access, e.g. response.execution_status/response.error/
# response.findings, read directly from those component files before
# writing this router). No new orchestrator, no new LLM call, no new
# prompt builder -- those never existed as committed code, and adding them
# would be new architecture this MWO does not authorize.
#
# DATA_GAP, not 404: build_engineering_insight() already returns None
# (never fabricates) when knowledge.recommendation is empty -- mapped here
# to execution_status="DATA_GAP" with no `error` field set, so
# statusVariant()/statusLabel() (engineeringAIRender.js) render an
# "attention" badge reading "DATA_GAP", not the "critical" red "Error"
# badge a missing route produced. A pump that truly does not exist (or is
# out of the caller's Area/MA scope) still 404s via the same
# _guard_tag_in_scope() every other per-tag pump route already uses --
# real NOT_FOUND stays allowed, per this MWO's own Phase 2 contract.

# Permission name matches the already-committed, already-tested
# ROLE_PERMISSIONS contract (test_auth_router.py's own
# test_pertamina_engineer_has_engineering_ai_ask / test_tap_engineer_
# has_engineering_ai_ask / test_pertamina_viewer_lacks_engineering_ai_ask)
# -- reused, not invented.
router = APIRouter(dependencies=[Depends(require_permission("engineering_ai.ask"))])

_PROVIDER_LABEL = "DETERMINISTIC_RULE_ENGINE"


class EngineeringAIAskRequest(BaseModel):
    asset_code: str
    intent: str
    prompt_type: str
    trace_id: str
    question: str | None = None
    workspace: str | None = None


def _data_gap_response(trace_id: str, latency: float, message: str) -> dict[str, Any]:
    return {
        "execution_status": "DATA_GAP",
        "summary": message,
        "risk": None,
        "confidence": None,
        "remaining_life": None,
        "findings": [],
        "evidence": [],
        "recommendations": [],
        "source_references": [],
        "provider": _PROVIDER_LABEL,
        "latency": latency,
        "trace_id": trace_id,
    }


@router.post("/api/ltsa/engineering-ai")
def post_engineering_ai(
    payload: EngineeringAIAskRequest,
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    engineering_context_engine=Depends(get_engineering_context_engine),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    tag = payload.asset_code
    # Real NOT_FOUND stays allowed. _guard_tag_in_scope alone is not
    # enough here: for a full-access (unscoped) caller it is a no-op
    # (routers/pumps.py's own sub-resource routes rely on the downstream
    # data source naturally coming back empty for an unknown tag instead)
    # -- this endpoint has no such downstream "empty means not found"
    # signal (LTSAKnowledgeService.build() never itself 404s), so a
    # genuinely unknown pump needs its own explicit existence check before
    # _guard_tag_in_scope's own out-of-scope check runs.
    pump_response = pump_gateway.get_pump(tag)
    if not isinstance(pump_response, dict) or not pump_response.get("success") or not pump_response.get("data"):
        raise HTTPException(status_code=404, detail="Pump not found")
    _guard_tag_in_scope(tag, pump_gateway, current_user)

    started = time.monotonic()
    try:
        knowledge = ltsa_knowledge_service.build(tag)
        summary = engineering_context_engine.build(tag)
    except Exception as error:  # noqa: BLE001 -- a downstream failure must produce an honest error response, never an unhandled 500 or a fabricated SUCCESS.
        latency = time.monotonic() - started
        response = _data_gap_response(payload.trace_id, latency, "Engineering AI data is currently unavailable.")
        response["execution_status"] = "ERROR"
        response["error"] = str(error) or "Engineering AI data is currently unavailable."
        return response

    insight = build_engineering_insight(knowledge.recommendation or (), summary)
    latency = time.monotonic() - started

    if insight is None:
        return _data_gap_response(
            payload.trace_id,
            latency,
            "No engineering recommendation available for this asset yet -- insufficient LTSA "
            "evidence (PM/CM/CMON/installation history) to generate a grounded recommendation.",
        )

    top_recommendation = knowledge.recommendation[0]
    evidence = [
        f"{item.source} {item.reference} -- {item.field}: {item.value}"
        for item in (top_recommendation.evidence or ())
    ]

    return {
        "execution_status": "SUCCESS",
        "summary": insight.root_cause,
        "risk": insight.risk,
        "confidence": insight.confidence,
        "remaining_life": None,
        "findings": [insight.root_cause],
        "evidence": evidence,
        "recommendations": [insight.recommended_action],
        "source_references": [],
        "provider": _PROVIDER_LABEL,
        "latency": latency,
        "trace_id": payload.trace_id,
    }
