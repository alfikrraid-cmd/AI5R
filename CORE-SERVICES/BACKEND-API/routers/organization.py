from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name, require_permission
from models.responses import Payload
from API.organization_registry import get_organization as _get_organization

# MWO-LTSA-AUTH-001 -- authenticated-only (no specific customer-facing
# permission fits company metadata; pump.read is the broadest baseline
# "logged in as any LTSA role" gate already granted to every V1 role).
router = APIRouter(dependencies=[Depends(require_permission("pump.read"))])


@router.get("/organization")
def get_organization(product_name: str = Depends(get_product_name)) -> Payload:
    return _get_organization(product_name)
