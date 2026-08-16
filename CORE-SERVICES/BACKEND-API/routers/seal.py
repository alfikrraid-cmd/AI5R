from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import (
    get_seal_gateway,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001 -- seal.read gates seal identity/compatibility data
# for the whole router; seal-stock additionally requires inventory.read
# (stacked below), since stock QUANTITY is a distinct permission from
# seal IDENTITY in this MWO's own requested permission set.
router = APIRouter(dependencies=[Depends(require_permission("seal.read"))])

# Mechanical Seal Workspace API (MWO-LTSA-041, per MWO-LTSA-040's
# archaeology) -- reuses SealGateway/SealStockGateway/
# SealPumpCompatibilityGateway unmodified, exposed under the /api/ltsa
# prefix already used by every other LTSA registry endpoint (mirrors
# pumps.py's list_ltsa_pumps pass-through exactly). No new gateway,
# service, repository, workflow, or SQL -- these three Gateways and their
# n8n workflows already existed; only the router layer was missing. List
# only, matching each Gateway's own real capability -- create/detail/
# update/delete are out of this MWO's scope.


@router.get("/api/ltsa/seals")
def list_ltsa_seals(seal_gateway=Depends(get_seal_gateway)) -> Payload:
    return seal_gateway.list_seals()


@router.get("/api/ltsa/seal-stock")
def list_ltsa_seal_stock(
    seal_stock_gateway=Depends(get_seal_stock_gateway),
    _stock_permission=Depends(require_permission("inventory.read")),
) -> Payload:
    return seal_stock_gateway.list_seal_stocks()


@router.get("/api/ltsa/seal-compatibility")
def list_ltsa_seal_compatibility(
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
) -> Payload:
    return seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
