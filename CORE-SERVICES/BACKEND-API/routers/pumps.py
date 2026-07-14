from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_pump_gateway
from models.responses import Payload

router = APIRouter()


@router.get("/pumps")
def list_pumps(pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.list_pumps()


@router.get("/pumps/{tag}")
def get_pump(tag: str, pump_gateway=Depends(get_pump_gateway)) -> Payload:
    return pump_gateway.get_pump(tag)
