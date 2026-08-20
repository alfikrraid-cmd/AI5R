from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies import (
    get_current_user,
    get_pump_gateway,
    get_seal_gateway,
    get_seal_master_data_repository,
    get_seal_pump_compatibility_gateway,
    get_seal_stock_gateway,
    get_seal_unit_repository,
    require_permission,
)
from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import filter_records_by_asset_scope
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


# MWO-LTSA-SEAL-UNIT-IDENTITY-FOUNDATION-001 -- read support only (no
# create/install/remove/repair route) for the new physical-seal-identity
# primitive. Deliberately UNSCOPED, mirroring list_ltsa_seals/
# list_ltsa_seal_stock above, not list_ltsa_seal_compatibility's
# per-pump-row scoping: seal_unit's primary identity is seal-catalog-
# shaped (like seal_registry), and a unit's current_pump_tag_number is
# explicitly current-state-only, not the row's ownership. This mirrors
# the existing, already-intentional "seal.read exposes the seal catalog
# globally" policy rather than silently introducing a new one -- flagged
# in this MWO's own completion report for explicit Chief Architect
# confirmation, not decided unilaterally here.
@router.get("/api/ltsa/seal-units")
def list_ltsa_seal_units(seal_unit_repository=Depends(get_seal_unit_repository)) -> Payload:
    data = seal_unit_repository.list_all()
    return {"data": data, "count": len(data)}


@router.get("/api/ltsa/seal-units/{seal_unit_id}")
def get_ltsa_seal_unit(seal_unit_id: str, seal_unit_repository=Depends(get_seal_unit_repository)) -> Payload:
    unit = seal_unit_repository.find_by_id(seal_unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="No such seal unit")
    return {"data": unit}


@router.get("/api/ltsa/seal-stock")
def list_ltsa_seal_stock(
    seal_stock_gateway=Depends(get_seal_stock_gateway),
    _stock_permission=Depends(require_permission("inventory.read")),
) -> Payload:
    return seal_stock_gateway.list_seal_stocks()


@router.get("/api/ltsa/seal-compatibility")
def list_ltsa_seal_compatibility(
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- each row carries
    # pump_tag_number (not asset_code); list_ltsa_seals/list_ltsa_seal_stock
    # above are deliberately left unscoped (a seal_code has no single-area
    # ownership of its own -- "DO NOT invent ownership"), but a
    # compatibility ROW is genuinely single-pump-attributable.
    response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        filtered = filter_records_by_asset_scope(
            response["data"], scope, pump_gateway, asset_field="pump_tag_number"
        )
        response = {**response, "data": filtered, "count": len(filtered)}
    return response


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
