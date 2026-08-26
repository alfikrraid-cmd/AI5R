from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from API.auth_service import AuthenticatedIdentity
from API.mechanical_seal_stock_repository import can_view_gpn
from dependencies import get_current_user, get_mechanical_seal_stock_repository, require_permission
from models.responses import Payload

router = APIRouter(dependencies=[Depends(require_permission("inventory.read"))])


@router.get("/api/ltsa/mechanical-seal-stock")
def list_mechanical_seal_stock(
    repository=Depends(get_mechanical_seal_stock_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=120),
    verification_status: str | None = Query(None),
) -> Payload:
    return repository.list_pools(
        limit=limit,
        offset=offset,
        search=search,
        verification_status=verification_status,
        include_gpn=can_view_gpn(current_user.role),
    )


@router.get("/api/ltsa/mechanical-seal-stock/{stock_pool_id}")
def get_mechanical_seal_stock(
    stock_pool_id: str,
    repository=Depends(get_mechanical_seal_stock_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    pool = repository.get_pool(stock_pool_id, include_gpn=can_view_gpn(current_user.role))
    if pool is None:
        raise HTTPException(status_code=404, detail="Mechanical seal stock pool not found")
    return {"success": True, "data": pool}
