from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_admin_service import (
    DelegationDeniedError,
    LastSuperuserError,
    authorize_user_management,
    guard_last_superuser,
)
from API.auth_password import hash_password
from API.auth_service import normalize_username
from dependencies import get_auth_repository, get_current_user
from models.requests import (
    AdminCreateUserRequest,
    AdminResetPasswordRequest,
    AdminUpdateMembershipRoleRequest,
    AdminUpdateUserStatusRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-003A-FINAL -- User Administration. Every route requires
# admin.users (SUPERUSER and TAP_ADMIN only, per ROLE_PERMISSIONS); which
# SPECIFIC target roles an admin.users holder may actually act on is a
# separate, per-request check (authorize_user_management, below) against
# auth_service.DELEGATION_SCOPE -- admin.users alone is necessary but not
# sufficient (a TAP_ADMIN request to manage a SUPERUSER or
# JOHN_CRANE_ENGINEER account is rejected with 403 even though the route
# itself was reachable).
#
# No route ever returns password_hash: list_users()'s own SELECT never
# reads that column (see auth_repository.list_users), and no response
# model here echoes the request's password/new_password field back.
router = APIRouter(dependencies=[Depends(get_current_user)])


def _user_summary(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row.get("username"),
        "email": row.get("email"),
        "status": row["user_status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_by": row.get("created_by"),
        "updated_by": row.get("updated_by"),
        "organization_id": row.get("organization_id"),
        "organization_code": row.get("organization_code"),
        "organization_name": row.get("organization_name"),
        "role": row.get("role"),
        "membership_status": row.get("membership_status"),
    }


def _require_admin_users(current_user) -> None:
    if "admin.users" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Missing permission: admin.users")


def _target_role_or_404(auth_repository, user_id: str, organization_id: str) -> str:
    membership = auth_repository.find_membership(user_id, organization_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="No such user/organization membership")
    return membership.role


@router.get("/api/admin/users")
def list_users(current_user=Depends(get_current_user), auth_repository=Depends(get_auth_repository)) -> Payload:
    _require_admin_users(current_user)
    return {"users": [_user_summary(row) for row in auth_repository.list_users()]}


@router.post("/api/admin/users")
def create_user(
    payload: AdminCreateUserRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_admin_users(current_user)
    try:
        authorize_user_management(current_user.role, payload.role)
    except DelegationDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error))

    try:
        username = normalize_username(payload.username)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if auth_repository.find_user_by_username(username) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    email = payload.email.strip().lower() if payload.email else None
    user_id = auth_repository.create_user(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        created_by=current_user.user_id,
    )
    auth_repository.create_membership(
        user_id=user_id,
        organization_id=payload.organization_id,
        role=payload.role,
        created_by=current_user.user_id,
    )
    return {"id": user_id, "username": username, "email": email, "organization_id": payload.organization_id, "role": payload.role}

@router.patch("/api/admin/users/{user_id}/status")
def update_user_status(
    user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_admin_users(current_user)
    membership = auth_repository.find_active_membership_for_user(user_id)
    target_role = membership.role if membership else None
    if target_role is not None:
        try:
            authorize_user_management(current_user.role, target_role)
        except DelegationDeniedError as error:
            raise HTTPException(status_code=403, detail=str(error))

    if payload.status != "ACTIVE":
        try:
            guard_last_superuser(
                target_is_active_superuser=auth_repository.is_active_superuser(user_id),
                active_superuser_count=auth_repository.count_active_superusers(),
                action="disable",
            )
        except LastSuperuserError as error:
            raise HTTPException(status_code=409, detail=str(error))

    auth_repository.update_user_status(user_id, payload.status, updated_by=current_user.user_id)
    return {"id": user_id, "status": payload.status}


@router.patch("/api/admin/users/{user_id}/role")
def update_membership_role(
    user_id: str,
    payload: AdminUpdateMembershipRoleRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_admin_users(current_user)
    current_role = _target_role_or_404(auth_repository, user_id, payload.organization_id)

    try:
        authorize_user_management(current_user.role, current_role)
        authorize_user_management(current_user.role, payload.role)
    except DelegationDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error))

    if current_role == "SUPERUSER" and payload.role != "SUPERUSER":
        try:
            guard_last_superuser(
                target_is_active_superuser=auth_repository.is_active_superuser(user_id),
                active_superuser_count=auth_repository.count_active_superusers(),
                action="demote",
            )
        except LastSuperuserError as error:
            raise HTTPException(status_code=409, detail=str(error))

    auth_repository.update_membership_role(
        user_id, payload.organization_id, payload.role, updated_by=current_user.user_id
    )
    return {"id": user_id, "organization_id": payload.organization_id, "role": payload.role}


@router.post("/api/admin/users/{user_id}/password-reset")
def reset_password(
    user_id: str,
    payload: AdminResetPasswordRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_admin_users(current_user)
    membership = auth_repository.find_active_membership_for_user(user_id)
    if membership is not None:
        try:
            authorize_user_management(current_user.role, membership.role)
        except DelegationDeniedError as error:
            raise HTTPException(status_code=403, detail=str(error))

    auth_repository.update_password_hash(
        user_id, hash_password(payload.new_password), updated_by=current_user.user_id
    )
    # Never echo the new password (or its hash) back, per Hard Rule 24.
    return {"id": user_id, "status": "password_reset"}
