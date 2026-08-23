"""MWO-AI5R-LTSA-COPILOT-001 -- LTSA Dashboard Copilot minimum vertical
slice. Deterministic, keyword-based intent dispatch over ALREADY-EXISTING
LTSA services (maintenance_intelligence_service, ltsa_knowledge_service,
equipment_timeline_service, installation_gateway, pump_area_scope) -- no
LLM, no new gateway/service/container/database/vector DB. Every handler is
a thin read + format over an existing, dependency-injected service call
(the exact same gateway-injection convention routers/pumps.py's own
sub-resource routes already use), never a fresh, ungated gateway
instance -- "reuse before create", the same discipline every other
CORE-SERVICES module in this repository follows.

IDENTITY SAFETY (Hard Rules, this MWO):
  - A tag is never invented, defaulted, or guessed from question text --
    the caller (router) supplies an already scope-checked `tag`, resolved
    from asset_context/workspace selection, never parsed out of free text.
  - "current seal" is answered ONLY via EquipmentTimelineService.
    build_current_seal(tag) -- the same authoritative per-tag source
    routers/pumps.py's own /knowledge endpoint already uses for
    `current_seal` -- never via LTSAKnowledge.seal (the broader
    *compatible* seals list) and never by reading any other tag's data.
    DE/NDE is a position recorded on whatever installation/reading record
    build_current_seal or get_pump_condition_monitoring_flag already
    surfaces -- this module adds no DE/NDE derivation of its own, so it
    cannot conflate a seal position with a separate pump identity.
  - Every handler below reads exactly the one `tag` it was given -- there
    is no code path here that reads from a second tag to answer a
    question about the first.

Server-side authorization/scope is NOT this module's concern: the router
(routers/copilot.py) resolves resolve_area_scope(current_user) and denies
an out-of-scope tag before ask_copilot() is ever called (same
"safe not-found" discipline as routers/pumps.py's own _guard_tag_in_scope).
The one exception is the global (tag-less) work-orders intent, which
IS scope-filtered here (via pump_area_scope.filter_records_by_asset_scope,
reused unmodified) since it has no single tag for the router to gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import maintenance_intelligence_service as mis
from .pump_area_scope import filter_records_by_asset_scope

FACT = "FACT"
INTERPRETATION = "INTERPRETATION"
RECOMMENDATION = "RECOMMENDATION"
DATA_GAP = "DATA_GAP"

_NO_INTENT_MESSAGE = (
    "I couldn't match that question to a supported topic. Try asking about "
    "pump status, pump history, installation, PM/CM, work orders, "
    "seal/compatibility, inventory/stock, drawing/document, or recommendation."
)
_NO_ASSET_MESSAGE = (
    "This question needs a specific pump/asset. Select an asset, or ask a "
    "fleet-wide question such as \"active work orders\"."
)


@dataclass(frozen=True, slots=True)
class CopilotAnswer:
    answer: str
    kind: str
    evidence: tuple[dict[str, Any], ...]


def _evidence(source: str, reference: str, field: str, value: Any) -> dict[str, Any]:
    return {"source": source, "reference": reference, "field": field, "value": "N/A" if value is None else str(value)}


# Ordered, most-specific-first -- first match wins. `current seal` is
# checked before the generic `seal` intent so "seal terakhir apa?" /
# "what's the current seal?" routes to the identity-safe single-record
# lookup instead of the broader compatibility list.
def _detect_intent(question: str) -> str | None:
    q = (question or "").lower()

    def has(*words: str) -> bool:
        return any(re.search(word, q) for word in words)

    if has(r"\bseal\b", r"\bsegel\b") and has("current", "terakhir", "latest", "sekarang", r"\bnow\b"):
        return "current_seal"
    if has("install"):
        return "installation"
    if has(r"\bpm\b", "preventive"):
        return "pm"
    if has(r"\bcm\b", "corrective", "breakdown", "kerusakan"):
        return "cm"
    if has("work order", "workorder", r"\bwo\b", "kerja"):
        return "work_orders"
    if has(r"\bseal\b", r"\bsegel\b", "compatib", "cocok"):
        return "seal_compat"
    if has("stock", "stok", "inventory", "inventaris", "spare part", "sparepart", "suku cadang"):
        return "inventory"
    if has("drawing", "gambar", "document", "dokumen"):
        return "drawing_document"
    if has("recommend", "rekomendasi", "saran"):
        return "recommendation"
    if has("history", "riwayat", "histori"):
        return "pump_history"
    if has("status", "kondisi"):
        return "pump_status"
    return None


def ask_copilot(
    question: str,
    tag: str | None,
    scope: frozenset[str] | None,
    *,
    pump_gateway,
    maintenance_history_gateway,
    work_order_gateway,
    installation_gateway,
    ltsa_knowledge_service,
    equipment_timeline_service,
) -> CopilotAnswer:
    intent = _detect_intent(question)

    if intent is None:
        return CopilotAnswer(_NO_INTENT_MESSAGE, DATA_GAP, ())

    if intent == "work_orders" and tag is None:
        return _handle_global_work_orders(scope, pump_gateway=pump_gateway, work_order_gateway=work_order_gateway)

    if tag is None:
        return CopilotAnswer(_NO_ASSET_MESSAGE, DATA_GAP, ())

    handler = TOOL_HANDLERS[intent]
    return handler(
        tag,
        pump_gateway=pump_gateway,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        installation_gateway=installation_gateway,
        ltsa_knowledge_service=ltsa_knowledge_service,
        equipment_timeline_service=equipment_timeline_service,
    )


def _handle_pump_status(tag: str, *, pump_gateway, **_: Any) -> CopilotAnswer:
    result = mis.get_pump_status(tag, pump_gateway=pump_gateway)
    pump = result.get("data")
    if not result.get("success") or not pump:
        return CopilotAnswer(f"Pump {tag} was not found.", DATA_GAP, ())
    answer = (
        f"{pump.get('tag_number', tag)} ({pump.get('pump_type', 'unknown type')}) is currently "
        f"{pump.get('status') or 'UNKNOWN'}, located at {pump.get('location') or 'an unknown location'} "
        f"in area {pump.get('area') or 'an unknown area'}."
    )
    evidence = (_evidence("PumpGateway", tag, "status", pump.get("status")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_pump_history(tag: str, *, maintenance_history_gateway, **_: Any) -> CopilotAnswer:
    result = mis.get_pump_history(tag, maintenance_history_gateway=maintenance_history_gateway)
    if not result.get("success"):
        return CopilotAnswer(f"Maintenance history for {tag} is currently unavailable.", DATA_GAP, ())
    records = result.get("records") or []
    if not records:
        return CopilotAnswer(f"No maintenance history found for pump {tag}.", FACT, ())
    lines = [
        f"- {r.get('maintenance_record_code')}: {r.get('action_taken')} by {r.get('performed_by') or 'unknown'} on {r.get('performed_at') or 'an unknown date'}"
        for r in records
    ]
    answer = f"Pump {tag} has {len(records)} maintenance record(s):\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("MaintenanceHistory", r.get("maintenance_record_code") or tag, "action_taken", r.get("action_taken"))
        for r in records
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_work_orders(tag: str, *, work_order_gateway, **_: Any) -> CopilotAnswer:
    result = mis.get_active_work_orders(tag, work_order_gateway=work_order_gateway)
    if not result.get("success"):
        return CopilotAnswer(f"Work order data for {tag} is currently unavailable.", DATA_GAP, ())
    work_orders = result.get("work_orders") or []
    if not work_orders:
        return CopilotAnswer(f"No active work orders for pump {tag}.", FACT, ())
    lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} (assigned to {wo.get('assigned_to') or 'nobody'})" for wo in work_orders]
    answer = f"{len(work_orders)} active work order(s) for pump {tag}:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("WorkOrderGateway", wo.get("work_order_code") or tag, "status", wo.get("status"))
        for wo in work_orders
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_global_work_orders(scope: frozenset[str] | None, *, pump_gateway, work_order_gateway) -> CopilotAnswer:
    result = mis.get_active_work_orders(work_order_gateway=work_order_gateway)
    if not result.get("success"):
        return CopilotAnswer("Work order data is currently unavailable.", DATA_GAP, ())

    work_orders = result.get("work_orders") or []
    if scope is not None:
        work_orders = filter_records_by_asset_scope(work_orders, scope, pump_gateway)

    if not work_orders:
        return CopilotAnswer("No active work orders in your authorized scope.", FACT, ())

    lines = [f"- {wo.get('work_order_code')}: {wo.get('status') or 'OPEN'} ({wo.get('asset_code') or 'N/A'})" for wo in work_orders]
    answer = f"{len(work_orders)} active work order(s) in your authorized scope:\n" + "\n".join(lines)
    evidence = tuple(
        _evidence("WorkOrderGateway", wo.get("work_order_code") or "N/A", "status", wo.get("status")) for wo in work_orders
    )
    return CopilotAnswer(answer, FACT, evidence)


def _handle_pm(tag: str, **_: Any) -> CopilotAnswer:
    result = mis.get_pump_last_pm(tag)
    if not result.get("success"):
        return CopilotAnswer(f"PM history for {tag} is currently unavailable.", DATA_GAP, ())
    last_pm = result.get("last_pm")
    if not last_pm:
        return CopilotAnswer(f"No preventive maintenance (PM) record found for {tag}.", FACT, ())
    answer = f"{tag}'s last PM was on {last_pm.get('performed_at') or 'an unknown date'} (source: {last_pm.get('source') or 'N/A'})."
    evidence = (_evidence("PMHistory", tag, "performed_at", last_pm.get("performed_at")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_cm(tag: str, **_: Any) -> CopilotAnswer:
    result = mis.get_pump_last_cm(tag)
    if not result.get("success"):
        return CopilotAnswer(f"CM history for {tag} is currently unavailable.", DATA_GAP, ())
    last_cm = result.get("last_cm")
    if not last_cm:
        return CopilotAnswer(f"No corrective maintenance (CM) record found for {tag}.", FACT, ())
    answer = (
        f"{tag}'s last CM report is {last_cm.get('cm_report_code') or 'N/A'}, "
        f"severity {last_cm.get('severity') or 'N/A'}, status {last_cm.get('status') or 'N/A'}."
    )
    evidence = (_evidence("CMReport", last_cm.get("cm_report_code") or tag, "severity", last_cm.get("severity")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_current_seal(tag: str, *, equipment_timeline_service, **_: Any) -> CopilotAnswer:
    current_seal = equipment_timeline_service.build_current_seal(tag)
    if current_seal is None:
        # Absence of an installation record is NOT proof of "no seal" --
        # never fabricated as a fact (Hard Rule: "Current seal must come
        # from evidence/history").
        return CopilotAnswer(f"No confirmed current-seal installation record exists for {tag}.", DATA_GAP, ())
    answer = (
        f"{tag}'s current seal is {current_seal.seal_code or 'N/A'}"
        f"{f' ({current_seal.seal_name})' if current_seal.seal_name else ''}, "
        f"installed {current_seal.installed_at or 'on an unknown date'} "
        f"(source: {current_seal.source})."
    )
    evidence = (_evidence(current_seal.source, current_seal.installation_code or tag, "seal_code", current_seal.seal_code),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_seal_compat(tag: str, *, ltsa_knowledge_service, **_: Any) -> CopilotAnswer:
    knowledge = ltsa_knowledge_service.build(tag)
    seals = knowledge.seal or []
    if not seals:
        return CopilotAnswer(f"No compatible mechanical seals are registered for {tag}.", FACT, ())
    lines = [f"- {s.get('seal_code')}: {s.get('part_name') or 'N/A'}" for s in seals]
    answer = f"{len(seals)} compatible seal(s) for {tag}:\n" + "\n".join(lines)
    evidence = tuple(_evidence("SealPumpCompatibility", s.get("seal_code") or tag, "part_name", s.get("part_name")) for s in seals)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_inventory(tag: str, *, ltsa_knowledge_service, **_: Any) -> CopilotAnswer:
    knowledge = ltsa_knowledge_service.build(tag)
    inventory = knowledge.inventory or []
    if not inventory:
        return CopilotAnswer(f"No spare-part stock records are registered for {tag}'s compatible seals.", FACT, ())
    lines = [f"- {i.get('seal_code')}: qty on hand {i.get('quantity_on_hand') if i.get('quantity_on_hand') is not None else 'N/A'} ({i.get('location') or 'N/A'})" for i in inventory]
    answer = f"Spare-part stock for {tag}:\n" + "\n".join(lines)
    evidence = tuple(_evidence("SealStock", i.get("seal_code") or tag, "quantity_on_hand", i.get("quantity_on_hand")) for i in inventory)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_drawing_document(tag: str, *, ltsa_knowledge_service, **_: Any) -> CopilotAnswer:
    knowledge = ltsa_knowledge_service.build(tag)
    drawings = knowledge.drawings or []
    if not drawings:
        return CopilotAnswer(f"No drawings/documents found for {tag}'s compatible seals.", FACT, ())
    lines = [f"- {d.get('document_number') or d.get('drawing_id')}: {d.get('title') or 'N/A'} (rev {d.get('revision') or 'N/A'})" for d in drawings]
    answer = f"{len(drawings)} drawing(s)/document(s) for {tag}:\n" + "\n".join(lines)
    evidence = tuple(_evidence("SealEngineeringDocument", d.get("drawing_id") or tag, "revision", d.get("revision")) for d in drawings)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_installation(tag: str, *, installation_gateway, **_: Any) -> CopilotAnswer:
    response = installation_gateway.list_installations()
    if not response.get("success"):
        return CopilotAnswer(f"Installation data for {tag} is currently unavailable.", DATA_GAP, ())
    records = [r for r in (response.get("data") or []) if r.get("plant_equip_no") == tag]
    if not records:
        return CopilotAnswer(f"No installation report found for {tag}.", FACT, ())
    latest = records[-1]
    answer = f"{tag} has {len(records)} installation report(s); most recent: {latest.get('installation_code') or 'N/A'} dated {latest.get('report_date') or 'N/A'}."
    evidence = (_evidence("InstallationGateway", latest.get("installation_code") or tag, "report_date", latest.get("report_date")),)
    return CopilotAnswer(answer, FACT, evidence)


def _handle_recommendation(tag: str, *, ltsa_knowledge_service, **_: Any) -> CopilotAnswer:
    knowledge = ltsa_knowledge_service.build(tag)
    recommendations = knowledge.recommendation or ()
    if not recommendations:
        return CopilotAnswer(f"No active recommendations for {tag}.", FACT, ())
    top = recommendations[0]
    lines = [f"- [{rec.category}] {rec.title}: {rec.action}" for rec in recommendations]
    answer = f"{len(recommendations)} recommendation(s) for {tag} (top: {top.title}):\n" + "\n".join(lines)
    evidence = tuple(_evidence(ev.source, ev.reference, ev.field, ev.value) for rec in recommendations for ev in rec.evidence)
    return CopilotAnswer(answer, RECOMMENDATION, evidence)


# MWO-AI5R-LTSA-AI-ORCHESTRATION-001 -- exported (was module-private) so
# copilot_orchestrator.py can expose these exact same functions as
# AI-selectable TOOLS, without duplicating a single one of them. The
# orchestrator only ever picks a NAME from this dict's own keys (validated
# against its own fixed catalog before any call) -- an LLM can select
# which tool to run, never inject new code, arguments, or a query string.
TOOL_HANDLERS = {
    "pump_status": _handle_pump_status,
    "pump_history": _handle_pump_history,
    "work_orders": _handle_work_orders,
    "pm": _handle_pm,
    "cm": _handle_cm,
    "current_seal": _handle_current_seal,
    "seal_compat": _handle_seal_compat,
    "inventory": _handle_inventory,
    "drawing_document": _handle_drawing_document,
    "installation": _handle_installation,
    "recommendation": _handle_recommendation,
}


__all__ = [
    "CopilotAnswer", "ask_copilot", "TOOL_HANDLERS",
    "FACT", "INTERPRETATION", "RECOMMENDATION", "DATA_GAP",
]
