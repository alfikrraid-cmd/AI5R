from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import (
    get_seal_gateway,
    get_seal_master_data_repository,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    require_permission,
)
from API.seal_master_data_repository import normalize_identifier_field
from models.requests import SealIdentifierUpdateRequest
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


# MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- the first write route this
# router has ever had. Gated on master.edit, not seal.read: master.edit
# was reserved in advance for exactly this ("master DATA edit --
# pumps/seals canonical definitions, no current route", auth_service.py's
# own ROLE_PERMISSIONS header) and is currently granted only to SUPERUSER
# and TAP_ADMIN (confirmed by reading the real ROLE_PERMISSIONS dict --
# TAP_ENGINEER is NOT in that set today) -- TAP_ENGINEER, JOHN_CRANE_
# ENGINEER, and both Pertamina roles are read-only here without a new
# permission string having to be invented, and without widening an
# existing one to fit this UI (Phase 6's own explicit allowance).
# Bypasses SealGateway/n8n entirely (see
# seal_master_data_repository.py's own header for why) -- reads still go
# through GET /api/ltsa/seals unchanged (SELECT * there already returns
# the two new columns once migration 013 has run, no gateway/workflow
# edit needed).
@router.patch("/api/ltsa/seals/{seal_code}")
def update_seal_identifiers(
    seal_code: str,
    payload: SealIdentifierUpdateRequest,
    current_user=Depends(require_permission("master.edit")),
    seal_master_data_repository=Depends(get_seal_master_data_repository),
) -> Payload:
    updated = seal_master_data_repository.update_seal_identifiers(
        seal_code,
        kimap_pertamina=normalize_identifier_field(payload.kimap_pertamina),
        gpn_john_crane=normalize_identifier_field(payload.gpn_john_crane),
        # Server-derived from the verified bearer token, never from the
        # request body -- SealIdentifierUpdateRequest has no updated_by
        # field at all, so there is nothing for a client to spoof here
        # (Phase 18: "client cannot submit arbitrary creator identity").
        updated_by=current_user.user_id,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="No such seal")
    return {"data": updated}
