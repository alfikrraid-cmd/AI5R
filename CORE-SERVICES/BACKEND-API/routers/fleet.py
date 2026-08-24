from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.fleet_insight import build_fleet_insight
from dependencies import (
    get_basic_fleet_overview_service,
    get_current_user,
    get_fleet_executive_summary_service,
    get_fleet_reliability_service,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("pump.read"))])

# MWO-LTSA-038C -- Power BI dataset contract version. Reuses the exact
# same constant-plus-isoformat-timestamp convention
# EngineeringContextEngine.CONTEXT_VERSION already established, not a new
# pattern. Bump this only when the /api/ltsa/fleet/powerbi response shape
# itself changes.
DATASET_VERSION = "1.0.0"

# Fleet Reliability API (MWO-LTSA-037C) -- exposes the already-built
# FleetReliabilityService (MWO-LTSA-037B) via one endpoint. Router only:
# no filtering, no derivation, no business logic here -- .build()'s own
# result is used unchanged, the same "reused shape, not redefined"
# discipline pumps.py's Knowledge endpoint already follows. One Aggregate
# (FleetReliabilityService), One API (this single route) -- no Bad Actor,
# Site KPI, or Trend endpoint here, since FleetReliabilityService itself
# does not compute them (explicitly out of MWO-LTSA-037B's own scope).


# Basic Fleet Overview API (MWO-LTSA-DASHBOARD-RECOVERY-001) -- the
# Executive Dashboard's core Fleet Overview panel calls this, not
# /reliability or /powerbi: those two require a per-pump
# LTSAKnowledgeService.build() fan-out (via FleetReliabilityService) that
# times out against a real fleet. This endpoint is bounded -- one call
# per canonical bulk-list gateway -- and safe to load synchronously on
# every dashboard visit.


@router.get("/api/ltsa/fleet/overview")
def get_fleet_overview(
    basic_fleet_overview_service=Depends(get_basic_fleet_overview_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    overview = basic_fleet_overview_service.build(scope=resolve_area_scope(current_user))

    return {
        "success": True,
        "data": dataclasses.asdict(overview),
    }


@router.get("/api/ltsa/fleet/reliability")
def get_fleet_reliability(
    fleet_reliability_service=Depends(get_fleet_reliability_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- scope is passed into
    # build() itself (filtered at pump discovery, before aggregation),
    # never applied to the finished snapshot -- a scoped identity's
    # pump_count/totals are genuinely recomputed from only their pumps.
    fleet_reliability = fleet_reliability_service.build(scope=resolve_area_scope(current_user))

    return {
        "success": True,
        "data": dataclasses.asdict(fleet_reliability),
    }


# Power BI API (MWO-LTSA-038A) -- one endpoint, one fetch, exposing
# FleetExecutiveSummary (MWO-LTSA-037E) and FleetInsight (MWO-LTSA-037F)
# together. Router only: no filtering, no derivation -- .build()'s own
# result and build_fleet_insight()'s own pure field selection over that
# same result are used unchanged. FleetExecutiveSummaryService already
# reuses FleetReliabilityService internally (MWO-LTSA-037E), so this is
# still exactly one HTTP round trip for an external consumer (Power BI),
# never a second backend call for the insight.


@router.get("/api/ltsa/fleet/powerbi")
def get_fleet_powerbi(
    fleet_executive_summary_service=Depends(get_fleet_executive_summary_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    summary = fleet_executive_summary_service.build(scope=resolve_area_scope(current_user))
    insight = build_fleet_insight(summary)

    return {
        "success": True,
        # MWO-LTSA-038C -- dataset contract envelope metadata: describes
        # this response (which schema version, generated when), not fleet
        # data, so it sits alongside "data" (like get_ltsa_pump_knowledge's
        # own tag_number), never inside it. generated_at is computed fresh
        # on every request -- no scheduler, no refresh job, no cache.
        "dataset_version": DATASET_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            **dataclasses.asdict(summary),
            "insight": dataclasses.asdict(insight) if insight is not None else None,
        },
    }
