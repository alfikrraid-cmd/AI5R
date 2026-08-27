from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.engineering_insight import build_engineering_insight
from API.pump_area_scope import filter_records_by_scope, is_area_in_scope
from API.executive_metrics import compute_executive_metrics
from API.maintenance_intelligence_service import (
    get_active_work_orders,
    get_pump_condition_monitoring_flag,
    get_pump_last_cm,
    get_pump_last_pm,
    get_pump_spare_parts,
)
from dependencies import (
    get_cm_report_gateway,
    get_condition_monitoring_reading_gateway,
    get_current_user,
    get_engineering_context_engine,
    get_equipment_timeline_service,
    get_ltsa_knowledge_service,
    get_maintenance_history_gateway,
    get_pm_occurrence_gateway,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    get_work_order_gateway,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001 -- router-level permission, applied to every route in
# this file via FastAPI's own dependencies=[...] mechanism (deny by
# default; endpoints ask for permissions, never scattered role checks).
router = APIRouter(dependencies=[Depends(require_permission("pump.read"))])


# MWO-LTSA-AUTH-DATA-SCOPE-CLOSURE-001 -- backend-enforced Area/MA data
# scope (never frontend-only filtering). scope=None means unrestricted
# (SUPERUSER/TAP_ADMIN/TAP_ENGINEER/JOHN_CRANE_ENGINEER, always); a
# Pertamina identity with no recognized scope gets an EMPTY frozenset,
# so both branches below correctly yield zero records/404 rather than
# accidentally falling through to "unrestricted".
@router.get("/pumps")
def list_pumps(
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pump_gateway.list_pumps()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        response = {**response, "data": filter_records_by_scope(response["data"], scope)}
        response["count"] = len(response["data"])
    return response


@router.get("/pumps/{tag}")
def get_pump(
    tag: str,
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pump_gateway.get_pump(tag)
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict):
        # Safe not-found semantics: a genuinely missing tag and an
        # out-of-scope tag must be INDISTINGUISHABLE to the caller (never
        # a 403, and never a different status/shape than a real miss --
        # otherwise the response itself would leak "this tag exists, you
        # just can't see it"). This route has no pre-existing tested
        # not-found convention of its own to mirror (unlike routers/
        # seal.py's "No such X" 404), so both cases are made to share
        # the SAME 404 here.
        data = response.get("data")
        if not isinstance(data, dict) or not is_area_in_scope(data.get("area"), scope):
            raise HTTPException(status_code=404, detail="Pump not found")
    return response


# Pump Registry API (WO-PUMP-001) -- same PumpGateway, exposed under the
# /api/ltsa prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001's identical addition for Work Order.


@router.get("/api/ltsa/pumps")
def list_ltsa_pumps(
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return list_pumps(pump_gateway=pump_gateway, current_user=current_user)


@router.get("/api/ltsa/pumps/{tag}")
def get_ltsa_pump(
    tag: str,
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return get_pump(tag, pump_gateway=pump_gateway, current_user=current_user)


# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- every /pumps/{tag}/...
# sub-resource route below aggregates data FOR tag itself (workorders,
# last-pm/last-cm/condition-monitoring-flag, spare-parts, knowledge,
# lifecycle) -- tag IS the pump, so the same is_area_in_scope() check
# get_pump() already performs applies directly, no asset_code indirection
# needed. Same safe not-found semantics: an out-of-scope tag's
# sub-resource 404s exactly like a request for a tag that does not exist.
def _guard_tag_in_scope(tag: str, pump_gateway, current_user: AuthenticatedIdentity) -> None:
    scope = resolve_area_scope(current_user)
    if scope is None:
        return
    response = pump_gateway.get_pump(tag)
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict) or not is_area_in_scope(data.get("area"), scope):
        raise HTTPException(status_code=404, detail="Pump not found")


# Open Work Orders / openWO (WO-PUMP-003) -- per ADR-PUMP-001, openWO is
# Derived, owned by Work Order, not a ltsa_pumps column. Delegates entirely
# to the existing maintenance_intelligence_service.get_active_work_orders(),
# which already filters WorkOrderGateway.list_work_orders() by asset_code
# and not closed_at -- no new gateway, no duplicated filter logic.


@router.get("/api/ltsa/pumps/{tag}/workorders")
def get_ltsa_pump_open_work_orders(
    tag: str,
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    result = get_active_work_orders(tag, work_order_gateway=work_order_gateway)
    work_orders = result.get("work_orders") or []

    return {
        "success": result.get("success", False),
        "tag_number": tag,
        "openWO": len(work_orders),
        "data": work_orders,
    }


# Last PM / lastPM (WO-PUMP-004, per ADR-PUMP-002; updated under
# MWO-MAINTINT-001 per ADR-PM-OCCURRENCE-001) -- lastPM is Derived,
# considering both a Work-Order-linked maintenance_history record
# (ADR-PUMP-002's original source, still valid) and the canonical
# pm_occurrence log (ADR-PM-OCCURRENCE-001), returning whichever is more
# recent. Delegates entirely to the existing
# maintenance_intelligence_service.get_pump_last_pm(), unmodified beyond
# its own MWO-MAINTINT-001 update -- no new gateway, no duplicated logic.


@router.get("/api/ltsa/pumps/{tag}/last-pm")
def get_ltsa_pump_last_pm(
    tag: str,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    return get_pump_last_pm(
        tag,
        maintenance_history_gateway=maintenance_history_gateway,
        work_order_gateway=work_order_gateway,
        pm_occurrence_gateway=pm_occurrence_gateway,
    )


# Last CM / lastCM and Condition Monitoring Flag (WO-ASSET360-001, per
# ADR-ASSET360-001) -- both Derived, both delegate entirely to the
# existing maintenance_intelligence_service functions -- no new gateway,
# no duplicated logic.


@router.get("/api/ltsa/pumps/{tag}/last-cm")
def get_ltsa_pump_last_cm(
    tag: str,
    cm_report_gateway=Depends(get_cm_report_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    return get_pump_last_cm(tag, cm_report_gateway=cm_report_gateway)


@router.get("/api/ltsa/pumps/{tag}/condition-monitoring-flag")
def get_ltsa_pump_condition_monitoring_flag(
    tag: str,
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    return get_pump_condition_monitoring_flag(
        tag, condition_monitoring_reading_gateway=condition_monitoring_reading_gateway
    )


# Spare Parts / Inventory Context Experience (MWO-INV-CTX-001) -- engineering
# context only, not warehouse management: which seals are compatible with
# this pump and their current stock, read-only. Delegates entirely to the
# existing maintenance_intelligence_service.get_pump_spare_parts(), which
# joins the Seal domain's existing seal_pump_compatibility/seal_stock/
# seal_registry data (MWO-LTSA-030, previously schema-only) -- no new
# gateway logic here, no persistence, no create/update/delete route.


@router.get("/api/ltsa/pumps/{tag}/spare-parts")
def get_ltsa_pump_spare_parts(
    tag: str,
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    seal_stock_gateway=Depends(get_seal_stock_gateway),
    seal_gateway=Depends(get_seal_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    return get_pump_spare_parts(
        tag,
        seal_pump_compatibility_gateway=seal_pump_compatibility_gateway,
        seal_stock_gateway=seal_stock_gateway,
        seal_gateway=seal_gateway,
    )


# Knowledge API (MWO-LTSA-031D) -- assembles LTSAKnowledgeService's
# (MWO-LTSA-031A), EquipmentTimelineService's (MWO-LTSA-031B/R1), and
# EngineeringContextEngine's already-existing outputs into one response.
# Router only: no filtering, no derivation, no business logic here --
# each service's own .build(tag) result is used unchanged, avoiding a
# second, drifting definition of a shape that already lives elsewhere
# (the same discipline models/responses.py's Payload comment documents
# for every other pass-through endpoint in this file).


@router.get("/api/ltsa/pumps/{tag}/knowledge")
def get_ltsa_pump_knowledge(
    tag: str,
    ltsa_knowledge_service=Depends(get_ltsa_knowledge_service),
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    engineering_context_engine=Depends(get_engineering_context_engine),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    knowledge = ltsa_knowledge_service.build(tag)
    build_with_knowledge = getattr(equipment_timeline_service, "build_with_knowledge", None)
    timeline = (
        build_with_knowledge(tag, knowledge)
        if build_with_knowledge is not None
        else equipment_timeline_service.build(tag)
    )
    summary = engineering_context_engine.build(tag)
    ai_insight = build_engineering_insight(knowledge.recommendation or (), summary)
    executive_metrics = compute_executive_metrics(knowledge)
    # MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- reuses
    # EquipmentTimelineService.build_lifecycle()'s own current-seal
    # resolution (already relied on by GET .../lifecycle and already
    # proven correct there) via its small build_current_seal() entry
    # point, instead of a second frontend fetch or a duplicated
    # derivation. Only fields with an authoritative source are ever
    # populated -- see _build_current_seal's own header comment.
    current_seal = equipment_timeline_service.build_current_seal(tag)
    # MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B (items A/B/E/F) -- reuses
    # the SAME build_lifecycle() already relied on by GET .../lifecycle
    # (below), passed the SAME already-built `knowledge` object above (no
    # second LTSAKnowledgeService.build() call) -- this is the one place
    # that already merges PM/CM/breakdown/work-order/installation/real
    # seal-lifecycle events into a single, full-timestamp, newest-first,
    # non-duplicating timeline (equipment_timeline_service.py's own
    # build_lifecycle()), plus its already-distinct documents list. No new
    # SQL, no new repository, no new merge/sort logic: only two additive
    # response keys exposing an aggregate that already existed.
    lifecycle = equipment_timeline_service.build_lifecycle(tag, knowledge=knowledge)
    # MWO-LTSA-ASSET360-SEAL-SEMANTICS-001 -- configured_seal reuses
    # knowledge.pump, the canonical pump record ltsa_knowledge_service.build()
    # already fetched above for this same response (no second gateway
    # call, no second fetch). This is deliberately a DIFFERENT concept from
    # current_seal: ltsa_pumps.seal_type/api_plan are broad master data
    # (production evidence: 16 different seal_registry T48MP variants
    # exist with different shaft_size values), never proof of which exact
    # seal is currently installed -- that remains current_seal's job
    # alone, never inferred from this.
    pump_record = knowledge.pump or {}
    configured_seal = {
        "seal_type": pump_record.get("seal_type"),
        "api_plan": pump_record.get("api_plan"),
    }
    # MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001 -- exposes
    # knowledge.pump (the same canonical pump record configured_seal above
    # already reuses -- no second gateway call, no second fetch) as its
    # own "pump" key, so Equipment Summary can show real area/location/
    # pump_type/status instead of the placeholder values
    # summary.asset (EngineeringContextEngine's own, narrower shape) never
    # carried. Passed through unchanged -- no new derivation.

    return {
        "success": True,
        "tag_number": tag,
        "data": {
            "summary": summary,
            "pump": knowledge.pump,
            "timeline": [dataclasses.asdict(event) for event in timeline.events],
            "seal": knowledge.seal,
            "current_seal": dataclasses.asdict(current_seal) if current_seal is not None else None,
            "configured_seal": configured_seal,
            "inventory": knowledge.inventory,
            "pm": knowledge.pm_history,
            "cm": knowledge.cm_history,
            "breakdown": knowledge.breakdown_history,
            "drawings": knowledge.drawings,
            # knowledge.recommendation is always a tuple from the real
            # LTSAKnowledgeService (MWO-LTSA-032C), but the field's type
            # remains `Any` -- a directly-constructed LTSAKnowledge (as
            # several existing tests' fakes do) can still legitimately
            # pass None, so this stays None-safe rather than assuming
            # non-None.
            "recommendation": (
                [dataclasses.asdict(rec) for rec in knowledge.recommendation]
                if knowledge.recommendation is not None
                else None
            ),
            # MWO-LTSA-035 -- deterministic AI Insight (EngineeringInsight):
            # pure field selection over knowledge.recommendation + summary,
            # no LLM, no network, no new derivation logic of its own -- see
            # engineering_insight.py's own header comment.
            "ai_insight": dataclasses.asdict(ai_insight) if ai_insight is not None else None,
            # MWO-LTSA-036E -- Knowledge Aggregate Extension (Asset360
            # Migration Roadmap Phase 2): additive keys on the same
            # response, no new endpoint, no second fetch.
            "pm_schedules": knowledge.pm_schedules,
            "condition_monitoring_schedules": knowledge.condition_monitoring_schedules,
            # MWO-LTSA-ASSET360-CONSOLIDATION-001 -- additive keys on the
            # same response (no new endpoint, no second fetch), same
            # precedent as MWO-LTSA-036E above. condition_monitoring_readings
            # was already assembled by LTSAKnowledgeService (MWO-LTSA-031A)
            # but never previously serialized here; work_orders is a new
            # field on the same LTSAKnowledge aggregate (see
            # ltsa_knowledge_service.py's own header note on this MWO).
            "condition_monitoring_readings": knowledge.condition_monitoring_readings,
            "work_orders": knowledge.work_orders,
            # MWO-LTSA-036O -- Executive Metrics: pure field derivation over
            # the already-built LTSAKnowledge (compute_executive_metrics,
            # MWO-LTSA-036N), same pass-through pattern as ai_insight above --
            # no new endpoint, no duplicate calculation. Always a real
            # ExecutiveMetrics (never None), so no None-guard is needed here.
            "executive_metrics": dataclasses.asdict(executive_metrics),
            # MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B (items A/B/E/F) --
            # additive keys, same pass-through convention as
            # executive_metrics/ai_insight above. lifecycle_timeline is
            # the complete, real-timestamp-ordered, multi-domain timeline
            # (including installation and real seal-lifecycle events,
            # never synthesized -- see equipment_timeline_service.py's
            # build_lifecycle()); it is additive alongside the existing
            # "timeline" key above (build()'s older, narrower timeline),
            # so no existing consumer of "timeline" is broken by this
            # change. documents is build_lifecycle()'s own, already
            # distinct-from-drawings document list.
            "lifecycle_timeline": [dataclasses.asdict(event) for event in lifecycle.timeline],
            "documents": lifecycle.related_engineering.documents,
        },
    }


# Pump Lifecycle API (MWO-LTSA-064A, finalizing the pre-existing
# EquipmentTimelineService.build_lifecycle()/PumpLifecycle DTOs) -- reuses
# the same get_equipment_timeline_service dependency and the exact
# dataclasses.asdict() pass-through pattern the /knowledge endpoint above
# already establishes for executive_metrics/ai_insight. Router only: no
# filtering, no derivation, no business logic here -- build_lifecycle()'s
# own result is returned unchanged.
@router.get("/api/ltsa/pumps/{tag}/lifecycle")
def get_ltsa_pump_lifecycle(
    tag: str,
    equipment_timeline_service=Depends(get_equipment_timeline_service),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    _guard_tag_in_scope(tag, pump_gateway, current_user)
    lifecycle = equipment_timeline_service.build_lifecycle(tag)

    return {
        "success": True,
        "tag_number": tag,
        "data": dataclasses.asdict(lifecycle),
    }

