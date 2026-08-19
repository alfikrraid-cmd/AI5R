from __future__ import annotations

from fastapi import APIRouter, Depends

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import is_area_in_scope, resolve_asset_area
from dependencies import (
    get_current_user,
    get_pump_gateway,
    get_seal_engineering_document_gateway,
    get_seal_pump_compatibility_gateway,
    require_permission,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])

# Document Workspace API (MWO-LTSA-062, Document & Drawing Productionization)
# -- reuses SealEngineeringDocumentGateway unmodified (built under
# MWO-LTSA-030/040B, already exposed via list_seal_engineering_documents(),
# already the real data source Drawing Workspace's own knowledge-endpoint
# path filters down to document_type == 'DRAWING'). This is the first
# router to expose the gateway's list() directly -- it was constructed in
# dependencies.py from the start but never wired into a router (confirmed
# gap, MWO-LTSA-060's own archaeology). No new gateway, service,
# repository, or workflow -- only the router layer was missing, mirroring
# seal.py's identical pass-through shape.
#
# Returns EVERY seal_engineering_document row (all seven document_type
# values, not just DRAWING) -- Document Workspace filters/groups
# client-side (documentMapping.js), the same way Seal.jsx/Pump.jsx already
# filter their own full-list responses. Drawing Workspace also reuses this
# same endpoint (not a second one) to resolve its own Document/Seal
# relationships -- see drawingMapping.js's own header comment for why.
#
# MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- a document row carries
# only seal_code, never asset_code/area. A seal is one-to-many with
# pumps (seal_pump_compatibility), so scope is resolved as: is this
# seal compatible with AT LEAST ONE in-scope pump? A seal with zero
# compatibility rows resolves to zero areas -- fail-closed for a scoped
# Pertamina identity, per this MWO's own "cannot be deterministically
# resolved -> fail closed" rule. Never a client-trusted area.


def _seals_in_scope(seal_pump_compatibility_gateway, pump_gateway, scope: frozenset[str]) -> set[str]:
    response = seal_pump_compatibility_gateway.list_seal_pump_compatibilities()
    rows = response.get("data") if isinstance(response, dict) else None
    if not isinstance(rows, list):
        return set()
    area_cache: dict[str, str | None] = {}
    in_scope: set[str] = set()
    for row in rows:
        seal_code = row.get("seal_code")
        tag = row.get("pump_tag_number")
        if not seal_code or seal_code in in_scope or not tag:
            continue
        if tag not in area_cache:
            area_cache[tag] = resolve_asset_area(tag, pump_gateway)
        if is_area_in_scope(area_cache[tag], scope):
            in_scope.add(seal_code)
    return in_scope


@router.get("/api/ltsa/documents")
def list_ltsa_documents(
    seal_engineering_document_gateway=Depends(get_seal_engineering_document_gateway),
    seal_pump_compatibility_gateway=Depends(get_seal_pump_compatibility_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = seal_engineering_document_gateway.list_seal_engineering_documents()
    scope = resolve_area_scope(current_user)
    if scope is not None and isinstance(response, dict) and isinstance(response.get("data"), list):
        allowed_seals = _seals_in_scope(seal_pump_compatibility_gateway, pump_gateway, scope)
        filtered = [r for r in response["data"] if r.get("seal_code") in allowed_seals]
        response = {**response, "data": filtered, "count": len(filtered)}
    return response
