from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_admin_service import (
    DelegationDeniedError,
    LastSuperuserError,
    authorize_user_management,
    guard_last_superuser,
)
from API.auth_password import hash_password
from API.auth_service import ROLE_PERMISSIONS, can_delegate_role, normalize_username
from API.whatsapp_registration_service import (
    IdentityNotPendingError,
    PhoneAlreadyBoundError,
    TargetMembershipInactiveError,
    TargetUserInactiveError,
    TargetUserNotFoundError,
    activate_whatsapp_identity,
    register_whatsapp_identity,
)
from dependencies import (
    get_auth_repository,
    get_current_user,
    get_record_change_history_repository,
    get_whatsapp_intake_repository,
)
from models.requests import (
    AdminActivateWhatsAppRequest,
    AdminCreateUserRequest,
    AdminRegisterWhatsAppRequest,
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
# TAP_ADMIN account is rejected with 403 even though the route
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


def _is_same_organization(current_user, organization_id: str | None) -> bool:
    return current_user.role == "SUPERUSER" or organization_id == current_user.organization_id


def _require_same_organization(current_user, organization_id: str | None) -> None:
    if not _is_same_organization(current_user, organization_id):
        raise HTTPException(status_code=403, detail="Cannot manage users outside your organization")


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=422, detail="Invalid email")
    return normalized


def _target_create_organization(current_user, requested_organization_id: str) -> str:
    if current_user.role == "TAP_ADMIN":
        _require_same_organization(current_user, requested_organization_id)
        return current_user.organization_id
    return requested_organization_id


def _with_manage_flag(row: dict, current_user) -> dict:
    summary = _user_summary(row)
    summary["can_manage"] = (
        summary.get("role") is not None
        and _is_same_organization(current_user, summary.get("organization_id"))
        and can_delegate_role(current_user.role, summary["role"])
    )
    return summary


def _require_admin_users(current_user) -> None:
    if "admin.users" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Missing permission: admin.users")


def _require_same_organization_as_target(current_user, auth_repository, user_id: str) -> None:
    # MWO-LTSA-WHATSAPP-ORG-BOUNDARY-001 -- same canonical organization
    # context every other admin_users.py route already uses (see
    # update_user_status/reset_password above): the target's SINGLE
    # canonical membership (auth_repository.find_active_membership_for_
    # user's own "earliest-created ACTIVE membership" rule -- the same
    # one-membership resolution login()/get_current_user() apply to the
    # ACTOR). A target with no active membership at all is intentionally
    # NOT rejected here -- that is whatsapp_registration_service's own
    # TargetMembershipInactiveError (404), not an org-boundary 403; this
    # check only ever fires when an active membership actually exists in
    # a DIFFERENT organization. SUPERUSER bypasses (_is_same_organization
    # itself already grants SUPERUSER, the same global semantics every
    # other route on this router already relies on).
    membership = auth_repository.find_active_membership_for_user(user_id)
    if membership is not None:
        _require_same_organization(current_user, membership.organization_id)


def _target_role_or_404(auth_repository, user_id: str, organization_id: str) -> str:
    membership = auth_repository.find_membership(user_id, organization_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="No such user/organization membership")
    return membership.role


@router.get("/api/admin/users")
def list_users(current_user=Depends(get_current_user), auth_repository=Depends(get_auth_repository)) -> Payload:
    _require_admin_users(current_user)
    return {"users": [_with_manage_flag(row, current_user) for row in auth_repository.list_users()]}


@router.post("/api/admin/users")
def create_user(
    payload: AdminCreateUserRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_admin_users(current_user)
    if payload.role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=422, detail="Unknown role")

    try:
        authorize_user_management(current_user.role, payload.role)
    except DelegationDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error))

    target_organization_id = _target_create_organization(current_user, payload.organization_id)
    if auth_repository.find_organization_by_id(target_organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        username = normalize_username(payload.username)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if auth_repository.find_user_by_username(username) is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    email = _normalize_email(payload.email)
    if email and auth_repository.find_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="Email already exists")

    try:
        user_id = auth_repository.create_user_with_membership(
            username=username,
            email=email,
            password_hash=hash_password(payload.password),
            organization_id=target_organization_id,
            role=payload.role,
            created_by=current_user.user_id,
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail="User creation failed before persistence completed") from error
    return {"id": user_id, "username": username, "email": email, "organization_id": target_organization_id, "role": payload.role}

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
        _require_same_organization(current_user, membership.organization_id)
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
    _require_same_organization(current_user, payload.organization_id)

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
        _require_same_organization(current_user, membership.organization_id)
        try:
            authorize_user_management(current_user.role, membership.role)
        except DelegationDeniedError as error:
            raise HTTPException(status_code=403, detail=str(error))

    auth_repository.update_password_hash(
        user_id, hash_password(payload.new_password), updated_by=current_user.user_id
    )
    # Never echo the new password (or its hash) back, per Hard Rule 24.
    return {"id": user_id, "status": "password_reset"}


# MWO-LTSA-WHATSAPP-ADMIN-REGISTRATION-001 -- admin-controlled WhatsApp
# sender registration. Same admin.users gate as every other route on this
# router; never authorizes based on WhatsApp-supplied input (the router
# never even sees an inbound WhatsApp message -- this is purely an admin
# action linking a phone to an EXISTING user). Registration/activation
# never assign or change role/scope -- those remain organization_
# memberships' own source of truth (see update_membership_role above).
@router.post("/api/admin/users/{user_id}/whatsapp/register")
def register_whatsapp_number(
    user_id: str,
    payload: AdminRegisterWhatsAppRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    whatsapp_repository=Depends(get_whatsapp_intake_repository),
    history_repository=Depends(get_record_change_history_repository),
) -> Payload:
    _require_admin_users(current_user)
    _require_same_organization_as_target(current_user, auth_repository, user_id)
    try:
        result = register_whatsapp_identity(
            target_user_id=user_id,
            phone_number=payload.phone_number,
            provider=payload.provider,
            actor_id=current_user.user_id,
            auth_repository=auth_repository,
            whatsapp_repository=whatsapp_repository,
            history_repository=history_repository,
        )
    except (TargetUserNotFoundError, TargetMembershipInactiveError) as error:
        raise HTTPException(status_code=404, detail=str(error))
    except TargetUserInactiveError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except PhoneAlreadyBoundError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        # normalize_sender_identifier's own ValueError (invalid phone
        # shape) -- a client input error, not a server error.
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": result}


@router.post("/api/admin/users/{user_id}/whatsapp/activate")
def activate_whatsapp_number(
    user_id: str,
    payload: AdminActivateWhatsAppRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    whatsapp_repository=Depends(get_whatsapp_intake_repository),
    history_repository=Depends(get_record_change_history_repository),
) -> Payload:
    _require_admin_users(current_user)
    _require_same_organization_as_target(current_user, auth_repository, user_id)
    try:
        result = activate_whatsapp_identity(
            target_user_id=user_id,
            sender_e164_sha256=payload.sender_e164_sha256,
            actor_id=current_user.user_id,
            whatsapp_repository=whatsapp_repository,
            history_repository=history_repository,
        )
    except TargetUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except IdentityNotPendingError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return {"data": result}
