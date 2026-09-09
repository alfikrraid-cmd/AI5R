"""MWO-LTSA-DASHBOARD-ANALYTICS-001 -- LTSA Dashboard Analytics Router.

Exposes server-side aggregations for the 7 LTSA dashboard domains:
- Reliability (KPIs, MTBF/MTTR policy, Bad Actors)
- PM / CM (Compliance, inspection coverage, trends)
- Breakdown (Work order breakdowns, failure events)
- Mechanical Seal Replacement (Seal life, failure patterns, leaks)
- Material Consumption (Stock usage, consumed spare parts)
- Inventory / Stock (Seal stock and compatibility)
- Maintenance Effectiveness (PM-to-CM ratio, proactive maintenance)

Gated by pump.read permission and scoped by resolve_area_scope(current_user).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.ltsa_analytics_service import LTSAAnalyticsService
from dependencies import (
    get_current_user,
    get_ltsa_analytics_service,
    require_permission,
)
from models.responses import Payload

router = APIRouter(dependencies=[Depends(require_permission("pump.read"))])


@router.get("/api/ltsa/analytics/filters")
def get_analytics_filters(
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    data = service.get_filter_options(scope=scope)
    return {
        "success": True,
        "data": data,
    }


@router.get("/api/ltsa/analytics/executive")
def get_executive_analytics(
    contract_area: str | None = Query(default=None),
    area: str | None = Query(default=None),
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    data = service.get_executive_analytics(
        contract_area=contract_area,
        area=area,
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
    contract_area: str | None = Query(default=None),
    area: str | None = Query(default=None),
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    data = service.get_seal_analytics(
        contract_area=contract_area,
        area=area,
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
    contract_area: str | None = Query(default=None),
    area: str | None = Query(default=None),
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    data = service.get_material_analytics(
        contract_area=contract_area,
        area=area,
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
    )
    return {
        "success": True,
        "data": data,
    }


@router.get("/api/ltsa/analytics/effectiveness")
def get_maintenance_effectiveness(
    contract_area: str | None = Query(default=None),
    area: str | None = Query(default=None),
    pump_tag: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: LTSAAnalyticsService = Depends(get_ltsa_analytics_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    data = service.get_maintenance_effectiveness(
        contract_area=contract_area,
        area=area,
        pump_tag=pump_tag,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
    )
    return {
        "success": True,
        "data": data,
    }

