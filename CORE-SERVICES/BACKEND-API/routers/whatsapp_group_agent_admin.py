"""
MWO-LTSA-TAP-GROUP-AGENT-001 Phase 2A -- admin lifecycle endpoints for
TAP LTSA WhatsApp group authorization (register -> PENDING, activate ->
ACTIVE, disable -> DISABLED). Gated by the SAME "admin.users" permission
admin_users.py's own router already requires -- reusing an existing,
already-granted admin capability rather than inventing a new permission
string with no role wired to it. No group can ever reach this endpoint
by messaging the agent; these are the only mutation paths, and every one
of them requires an authenticated admin identity (get_current_user),
never a client-supplied actor name -- registered_by/activated_by/
disabled_by are always current_user.user_id.

Never returns the raw WhatsApp group id in any response -- only its hash
and the admin-supplied display_label, matching "do not expose raw group
identifiers unnecessarily."
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from API.auth_service import AuthenticatedIdentity
from API.whatsapp_group_agent_service import GroupNotFoundError, hash_group_identifier
from dependencies import get_current_user, get_group_authorization_repository, require_permission

router = APIRouter(dependencies=[Depends(require_permission("admin.users"))])


class RegisterGroupRequest(BaseModel):
    group_id: str
    display_label: str


class ActivateGroupRequest(BaseModel):
    group_hash: str
    allowed_scope: list[str] | None = None


class DisableGroupRequest(BaseModel):
    group_hash: str


def _public(row: dict) -> dict:
    # Explicitly allow-listed projection -- never the raw group_id (which
    # is never stored in the first place), never anything beyond what an
    # admin needs to manage the lifecycle.
    allowed = {
        "group_hash", "display_label", "status", "allowed_scope",
        "registered_by", "registered_at", "activated_by", "activated_at",
        "disabled_by", "disabled_at",
    }
    return {key: value for key, value in row.items() if key in allowed}


@router.post("/api/ltsa/whatsapp-group/admin/register")
def register_group(
    payload: RegisterGroupRequest,
    repository=Depends(get_group_authorization_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> dict:
    group_hash = hash_group_identifier(payload.group_id)
    row = repository.register_group(
        group_hash=group_hash, display_label=payload.display_label, registered_by=current_user.user_id
    )
    return {"success": True, "data": _public(row)}


@router.post("/api/ltsa/whatsapp-group/admin/activate")
def activate_group(
    payload: ActivateGroupRequest,
    repository=Depends(get_group_authorization_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> dict:
    allowed_scope = frozenset(payload.allowed_scope) if payload.allowed_scope else None
    try:
        row = repository.activate_group(
            group_hash=payload.group_hash, activated_by=current_user.user_id, allowed_scope=allowed_scope
        )
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"success": True, "data": _public(row)}


@router.post("/api/ltsa/whatsapp-group/admin/disable")
def disable_group(
    payload: DisableGroupRequest,
    repository=Depends(get_group_authorization_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> dict:
    try:
        row = repository.disable_group(group_hash=payload.group_hash, disabled_by=current_user.user_id)
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"success": True, "data": _public(row)}


__all__ = ["router"]
