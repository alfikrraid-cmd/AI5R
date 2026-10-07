"""MWO-LTSA-DASHBOARD-ANALYTICS-001 -- LTSA Dashboard Analytics Router.

Exposes server-side aggregations for the 7 LTSA dashboard domains:
- Reliability (KPIs, MTBF/MTTR policy, Bad Actors)
- PM / CM (Compliance, inspection coverage, trends)
- Breakdown (Work order breakdowns, failure events)
- Mechanical Seal Installation (lifecycle events, leaks by pump type / API plan)
- Material Consumption (Stock usage, consumed spare parts)
- Inventory / Stock (Seal stock and compatibility)
- Maintenance Effectiveness (PM-to-CM ratio, proactive maintenance)

LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- gated by dashboard.read AND
pump.read. Every data route takes its scope from get_dashboard_scope
(resolve_area_scope(current_user) narrowed by ?area=; 403
area_not_in_scope / 422 invalid_area). The former raw area/contract_area
query parameters are no longer passed through: the selected area reaches
the service only as that narrowed, authorized scope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.ltsa_analytics_service import LTSAAnalyticsService
from API.pump_area_scope import authorized_area_options
from dependencies import (
    get_current_user,
    get_dashboard_scope,
    get_ltsa_analytics_service,
    require_permission,
)
from models.responses import Payload

router = APIRouter(
    dependencies=[Depends(require_permission("dashboard.read")), Depends(require_permission("pump.read"))]
)


@router.get("/api/ltsa/analytics/filters")
def get_analytics_filters(
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # Options always describe the caller's FULL authorization, independent
    # of any area currently selected on the dashboard.
    scope = resolve_area_scope(current_user)
    data = service.get_filter_options(scope=scope)
    return {
        "success": True,
        "data": {**data, "authorized_areas": authorized_area_options(scope)},
    }


@router.get("/api/ltsa/analytics/executive")
def get_executive_analytics(
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    scope: frozenset[str] | None = Depends(get_dashboard_scope),
) -> Payload:
    data = service.get_executive_analytics(
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
    )
    return {
        "success": True,
        "data": data,
    }


@router.get("/api/ltsa/analytics/seals")
def get_seal_analytics(
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    scope: frozenset[str] | None = Depends(get_dashboard_scope),
) -> Payload:
    data = service.get_seal_analytics(
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
    )
    return {
        "success": True,
        "data": data,
    }


@router.get("/api/ltsa/analytics/materials")
def get_material_analytics(
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    scope: frozenset[str] | None = Depends(get_dashboard_scope),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    data = service.get_material_analytics(
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
        include_internal_components="internal_component.read" in current_user.permissions,
    )
    return {
        "success": True,
        "data": data,
    }


@router.get("/api/ltsa/analytics/effectiveness")
def get_maintenance_effectiveness(
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    scope: frozenset[str] | None = Depends(get_dashboard_scope),
) -> Payload:
    data = service.get_maintenance_effectiveness(
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
    )
    return {
        "success": True,
        "data": data,
    }
