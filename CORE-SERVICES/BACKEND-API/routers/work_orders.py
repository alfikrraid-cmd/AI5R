from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_work_order_gateway
from models.requests import WorkOrderCreateRequest
from models.responses import Payload

router = APIRouter()


@router.post("/work-orders")
def create_work_order(
    payload: WorkOrderCreateRequest,
    work_order_gateway=Depends(get_work_order_gateway),
) -> Payload:
    return work_order_gateway.create_work_order(payload.model_dump())


@router.get("/work-orders/{id}")
def get_work_order(id: str, work_order_gateway=Depends(get_work_order_gateway)) -> Payload:
    return work_order_gateway.get_work_order(id)
