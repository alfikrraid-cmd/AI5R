from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import is_asset_in_scope, resolve_asset_area
from dependencies import (
    get_current_user,
    get_maintenance_history_gateway,
    get_pump_gateway,
    get_work_order_gateway,
    require_permission,
)
from models.requests import WorkOrderCreateRequest
from models.responses import Payload

# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- work_order.asset_type is
# polymorphic (PUMP/SEAL/ASSET/SOOT_BLOWER); only PUMP has a real
# area-resolution path today (get_ltsa_work_order_asset's own
# _ASSET_AREA_RESOLVERS, unchanged). A non-PUMP work order has no safe
# scope relation to invent -- "DO NOT invent ownership" -- so it is
# NEVER scope-filtered, only PUMP-typed records are. Never a client-
# trusted area: always re-resolved from asset_code via pump_gateway.
def _work_order_in_scope(record: dict, scope, pump_gateway) -> bool:
    if scope is None:
        return True
    if record.get("asset_type") != "PUMP":
        return True
    return is_asset_in_scope(record.get("asset_code"), scope, pump_gateway)

# MWO-LTSA-AUTH-001 -- maintenance.read gates every route in this file;
# the two create endpoints additionally require maintenance.write
# (stacked below) -- creating a work order is a state change, not a read.
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


@router.post("/work-orders")
def create_work_order(
    payload: WorkOrderCreateRequest,
    work_order_gateway=Depends(get_work_order_gateway),
    _write_permission=Depends(require_permission("maintenance.write")),
) -> Payload:
    return work_order_gateway.create_work_order(payload.model_dump())


@router.get("/work-orders/{id}")
def get_work_order(
    id: str,
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = work_order_gateway.get_work_order(id)
    scope = resolve_area_scope(current_user)
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict) and not _work_order_in_scope(data, scope, pump_gateway):
        raise HTTPException(status_code=404, detail="Work order not found")
    return response


# Work Order Registry API (WO-BE-001) -- same WorkOrderGateway, exposed under
# the /api/ltsa prefix already used by the Registry Workspace's other LTSA
# calls (ai5rClient.js). No new gateway, service, or repository layer.


@router.get("/api/ltsa/workorders")
def list_ltsa_work_orders(
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = work_order_gateway.list_work_orders()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = [r for r in response["data"] if _work_order_in_scope(r, scope, pump_gateway)]
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


@router.get("/api/ltsa/workorders/{id}")
def get_ltsa_work_order(
    id: str,
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return get_work_order(id, work_order_gateway=work_order_gateway, pump_gateway=pump_gateway, current_user=current_user)


@router.post("/api/ltsa/workorders")
def create_ltsa_work_order(
    payload: WorkOrderCreateRequest,
    work_order_gateway=Depends(get_work_order_gateway),
    _write_permission=Depends(require_permission("maintenance.write")),
) -> Payload:
    return work_order_gateway.create_work_order(payload.model_dump())


# Work Order Timeline (WO-BE-002) -- per ADR-WO-002, timeline is not a scalar
# on work_order; it is derived from the existing Maintenance History records
# linked by work_order_code. Delegates to the existing, unmodified
# MaintenanceHistoryGateway.list_maintenance_history() -- no new gateway, no
# duplicate timeline model. The only transformation is filtering the
# existing collection to this work order and correcting count to match; no
# maintenance_history record is reshaped.


@router.get("/api/ltsa/workorders/{id}/timeline")
def get_ltsa_work_order_timeline(
    id: str,
    maintenance_history_gateway=Depends(get_maintenance_history_gateway),
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # The work order itself (not each maintenance_history row) carries
    # asset_code/asset_type -- scope is resolved from that ONE lookup,
    # not per-row (a timeline belongs to a single work order/asset).
    scope = resolve_area_scope(current_user)
    if scope is not None:
        work_order = work_order_gateway.get_work_order(id)
        wo_data = work_order.get("data") if isinstance(work_order, dict) else None
        if isinstance(wo_data, dict) and not _work_order_in_scope(wo_data, scope, pump_gateway):
            raise HTTPException(status_code=404, detail="Work order not found")

    history = maintenance_history_gateway.list_maintenance_history()

    if not history.get("success"):
        return history

    timeline = [
        record
        for record in history.get("data") or []
        if record.get("work_order_code") == id
    ]

    return {"success": True, "count": len(timeline), "data": timeline}


# Work Order Asset / Area (WO-BE-003) -- per ADR-WO-002, area is not a
# work_order attribute; it is resolved from the existing polymorphic
# asset_code/asset_type reference against the owning Asset registry, the
# same PUMP/SEAL/ASSET/SOOT_BLOWER split MaintenanceRelationshipResolver
# already uses (PRODUCTS/LTSA-BRAIN/MAINTENANCE-FACTORY-PACK). Reuses the
# existing PumpGateway/get_pump unmodified -- no new registry gateway, no
# stored area on work_order. Only "PUMP" has a real registry gateway in
# CORE-SERVICES/API today; SEAL/ASSET/SOOT_BLOWER have canonical tables but
# no gateway yet, so they resolve as an explicit "unsupported asset_type"
# rather than a fabricated area.
_ASSET_AREA_RESOLVERS = {"PUMP"}


@router.get("/api/ltsa/workorders/{id}/asset")
def get_ltsa_work_order_asset(
    id: str,
    work_order_gateway=Depends(get_work_order_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    work_order = work_order_gateway.get_work_order(id)

    if not work_order.get("success"):
        return work_order

    record = work_order.get("data") or {}
    asset_code = record.get("asset_code")
    asset_type = record.get("asset_type")

    scope = resolve_area_scope(current_user)
    if scope is not None and not _work_order_in_scope(record, scope, pump_gateway):
        raise HTTPException(status_code=404, detail="Work order not found")

    if asset_type not in _ASSET_AREA_RESOLVERS:
        return {
            "success": False,
            "message": f"Unsupported asset_type for area resolution: {asset_type!r}",
            "asset_code": asset_code,
            "asset_type": asset_type,
            "area": None,
        }

    asset = pump_gateway.get_pump(asset_code)

    if not asset.get("success"):
        return {
            "success": False,
            "message": "Asset not found",
            "asset_code": asset_code,
            "asset_type": asset_type,
            "area": None,
        }

    return {
        "success": True,
        "message": "Asset area resolved",
        "asset_code": asset_code,
        "asset_type": asset_type,
        "area": (asset.get("data") or {}).get("area"),
    }
