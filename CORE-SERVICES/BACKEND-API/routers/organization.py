from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_product_name
from models.responses import Payload
from API.organization_registry import get_organization as _get_organization

router = APIRouter()


@router.get("/organization")
def get_organization(product_name: str = Depends(get_product_name)) -> Payload:
    return _get_organization(product_name)
