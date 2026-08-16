from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_work_order_gateway, require_permission
from models.requests import WorkOrderCreateRequest
from models.responses import Payload

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
def get_work_order(id: str, work_order_gateway=Depends(get_work_order_gateway)) -> Payload:
    return work_order_gateway.get_work_order(id)
