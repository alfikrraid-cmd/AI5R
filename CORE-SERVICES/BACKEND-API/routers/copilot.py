from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import is_area_in_scope
from API.copilot_orchestrator import orchestrate_copilot
from dependencies import (
    get_cm_report_repository,
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_copilot_ai_client,
    get_current_user,
    get_equipment_timeline_service,
    get_fleet_executive_summary_service,
    get_installation_gateway,
    get_installation_report_repository,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_mechanical_seal_stock_repository,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_repository,
    get_pm_schedule_repository,
    get_product_name,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_leak_diagnostic_service,
    get_seal_pump_compatibility_gateway,
    get_work_order_gateway,
    require_permission,
)
from models.requests import CopilotAskRequest
from models.responses import Payload
from API.maintenance_copilot import summarize_maintenance_situation as _summarize_maintenance_situation

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])
_PUMP_TAG_PATTERN = re.compile(
    r"(?<![A-Za-z0-9/-])(\d+)-?P-?(\d+)([A-Z])(?![A-Za-z0-9/-])",
    re.IGNORECASE,
)
_MULTIPLE_TAGS_MESSAGE = (
    "I found multiple pump tags in that question. Select one pump and ask again."
)


def _normalize_pump_tag(raw: str) -> str | None:
    match = _PUMP_TAG_PATTERN.fullmatch((raw or "").strip())
    if not match:
        return None
    return f"{match.group(1)}-P-{match.group(2)}{match.group(3).upper()}"


def _extract_pump_tag_candidates(question: str) -> tuple[str, ...]:
    """Extract explicit pump tags and normalize compact forms such as 110p12b."""
    return tuple(
        dict.fromkeys(
            f"{match.group(1)}-P-{match.group(2)}{match.group(3).upper()}"
            for match in _PUMP_TAG_PATTERN.finditer(question or "")
        )
    )


def _require_tag_in_scope(tag: str, pump_gateway, scope: frozenset[str] | None) -> None:
    response = pump_gateway.get_pump(tag)
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict) or not is_area_in_scope(data.get("area"), scope):
        # Preserve the existing safe-not-found response for unknown and
        # out-of-scope assets, regardless of how the tag was supplied.
        raise HTTPException(status_code=404, detail="Pump not found")


@router.get("/copilot/summary")
def copilot_summary(
    product_name: str = Depends(get_product_name),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- scope threads through
    # to get_maintenance_command_center's own pumps/work_orders/
    # maintenance_history filtering, applied before total_pumps/
    # active_work_orders/completed_today are counted and before
    # recent_work_orders/recent_maintenance are sliced.
    return _summarize_maintenance_situation(product_name, scope=resolve_area_scope(current_user))


# MWO-AI5R-LTSA-COPILOT-001 / MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- minimum
# vertical slice, now AI-orchestrated: intent dispatch/tool execution
# (API.copilot_ask_service, API.copilot_orchestrator) over already-existing
# LTSA services, gated by the exact same router-level permission
# (maintenance.read) and per-tag Area/MA scope guard every other
# /api/ltsa/pumps/{tag}/... route already establishes (routers/pumps.py's
# own _guard_tag_in_scope) -- out-of-scope/unknown tags 404 identically
# ("safe not-found", never a distinct status that would leak existence).
# A client-supplied asset_context is NEVER trusted as authorization by
# itself -- it is only a lookup key, re-checked against the caller's own
# server-resolved scope below BEFORE orchestrate_copilot() (AI or
# deterministic) ever reads its data.
@router.post("/api/ltsa/copilot/ask")
def ask_copilot_endpoint(
    payload: CopilotAskRequest,
    pump_gateway=Depends(get_pump_gateway),
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    installation_gateway=Depends(get_installation_gateway),
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    installation_report_repository=Depends(get_installation_report_repository),
    mechanical_seal_stock_repository=Depends(get_mechanical_seal_stock_repository),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    fleet_executive_summary_service=Depends(get_fleet_executive_summary_service),
    pm_occurrence_repository=Depends(get_pm_occurrence_repository),
    cm_report_repository=Depends(get_cm_report_repository),
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    seal_gateway=Depends(get_seal_gateway),
    seal_leak_diagnostic_service=Depends(get_seal_leak_diagnostic_service),
    ai_client=Depends(get_copilot_ai_client),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    tag = (payload.asset_context or "").strip() or None
    if tag is not None:
        tag = _normalize_pump_tag(tag) or tag

    if tag is not None:
        _require_tag_in_scope(tag, pump_gateway, scope)
    else:
        candidates = _extract_pump_tag_candidates(payload.question)
        if len(candidates) > 1:
            return {
                "answer": _MULTIPLE_TAGS_MESSAGE,
                "kind": "DATA_GAP",
                "evidence": [],
                "tools_used": [],
            }
        if candidates:
            tag = candidates[0]
            _require_tag_in_scope(tag, pump_gateway, scope)

    answer, tools_used = orchestrate_copilot(
        payload.question,
        tag,
        scope,
        ai_client,
        pump_gateway=pump_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        installation_gateway=installation_gateway,
        ltsa_knowledge_service=ltsa_knowledge_service,
        equipment_timeline_service=equipment_timeline_service,
        condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
        installation_report_repository=installation_report_repository,
        mechanical_seal_stock_repository=mechanical_seal_stock_repository,
        condition_monitoring_reading_repository=condition_monitoring_reading_repository,
        fleet_executive_summary_service=fleet_executive_summary_service,
        pm_occurrence_repository=pm_occurrence_repository,
        cm_report_repository=cm_report_repository,
        pm_cm_evidence_repository=pm_cm_evidence_repository,
        pm_schedule_repository=pm_schedule_repository,
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_gateway=seal_gateway,
        seal_leak_diagnostic_service=seal_leak_diagnostic_service,
    )

    # tools_used is additive/optional -- existing frontend (CopilotPanel/
    # useCopilot.js) reads only answer/kind/evidence and ignores unknown
    # keys, so this never breaks the pre-existing response contract.
    return {"answer": answer.answer, "kind": answer.kind, "evidence": list(answer.evidence), "tools_used": tools_used}
