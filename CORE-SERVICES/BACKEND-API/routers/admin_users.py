from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from API.auth_admin_service import (
    DelegationDeniedError,
    LastSuperuserError,
    authorize_user_management,
    guard_last_superuser,
)
from API.auth_password import PasswordPolicyError, hash_password, validate_password_policy
from API.auth_service import ROLE_PERMISSIONS, can_delegate_role, normalize_username
from API.password_reset_service import PasswordResetService
from API.whatsapp_registration_service import (
    IdentityNotPendingError,
    PhoneAlreadyBoundError,
    TargetMembershipInactiveError,
    TargetUserInactiveError,
    TargetUserNotFoundError,
    activate_whatsapp_identity,
    get_whatsapp_identity_status,
    register_whatsapp_identity,
)
from dependencies import (
    get_auth_repository,
    get_current_user,
    get_password_reset_service,
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
        "name": row.get("name"),
        "email": row.get("email"),
        "status": row["user_status"],
        "last_login": row.get("last_login"),
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


CREDENTIAL_MODE_EMAIL = "EMAIL_SET_PASSWORD"
CREDENTIAL_MODE_TEMPORARY = "TEMPORARY_PASSWORD"


def _resolve_credential_mode(payload) -> str:
    """Explicit credential_mode wins; when omitted, a supplied password
    means TEMPORARY_PASSWORD and no password means EMAIL_SET_PASSWORD."""
    mode = (payload.credential_mode or "").strip().upper()
    if not mode:
        return CREDENTIAL_MODE_TEMPORARY if payload.password else CREDENTIAL_MODE_EMAIL
    if mode not in (CREDENTIAL_MODE_EMAIL, CREDENTIAL_MODE_TEMPORARY):
        raise HTTPException(status_code=422, detail="Unknown credential_mode")
    if mode == CREDENTIAL_MODE_EMAIL and payload.password:
        raise HTTPException(status_code=422, detail="A password must not be supplied with EMAIL_SET_PASSWORD")
    return mode


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
        current_user.role == "SUPERUSER"
        or "admin.superuser" in current_user.permissions
    )
    return summary


def _require_admin_users(current_user) -> None:
    if "admin.users" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="Missing permission: admin.users")


def _require_superuser(current_user) -> None:
    if current_user.role != "SUPERUSER" and "admin.superuser" not in current_user.permissions:
        raise HTTPException(status_code=403, detail="SUPERUSER access required")


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
    _require_superuser(current_user)
    return {"users": [_with_manage_flag(row, current_user) for row in auth_repository.list_users()]}


@router.post("/api/admin/users")
def create_user(
    payload: AdminCreateUserRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Payload:
    _require_superuser(current_user)
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

    # LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- both modes create the user with
    # must_change_password=TRUE in the same statement as the user/membership
    # insert. EMAIL_SET_PASSWORD stores a random, never-disclosed password
    # (nobody can sign in with it) and emails a set-password link;
    # TEMPORARY_PASSWORD stores the admin-supplied, policy-checked password.
    credential_mode = _resolve_credential_mode(payload)
    if credential_mode == CREDENTIAL_MODE_EMAIL:
        if not email:
            raise HTTPException(status_code=422, detail="Email is required to send a set-password link")
        password_hash = hash_password(secrets.token_urlsafe(48))
    else:
        try:
            validate_password_policy(payload.password, username=username, email=email)
        except PasswordPolicyError as error:
            raise HTTPException(status_code=422, detail=str(error))
        password_hash = hash_password(payload.password)

    kwargs = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "organization_id": target_organization_id,
        "role": payload.role,
        "created_by": current_user.user_id,
        "must_change_password": True,
    }
    if payload.name is not None:
        kwargs["name"] = payload.name
    try:
        try:
            user_id = auth_repository.create_user_with_membership(**kwargs)
        except TypeError:
            kwargs.pop("name", None)
            user_id = auth_repository.create_user_with_membership(**kwargs)
    except Exception as error:
        raise HTTPException(status_code=500, detail="User creation failed before persistence completed") from error
    response = {
        "id": user_id,
        "username": username,
        "name": payload.name,
        "email": email,
        "organization_id": target_organization_id,
        "role": payload.role,
        "credential_mode": credential_mode,
        "must_change_password": True,
    }
    if credential_mode == CREDENTIAL_MODE_EMAIL:
        # The user exists either way; a failed dispatch is reported so the
        # admin can resend via POST .../set-password-link.
        sent = password_reset_service.send_set_password_link(user_id)
        response["set_password_email"] = "SENT" if sent else "FAILED"
    return response

@router.patch("/api/admin/users/{user_id}/status")
def update_user_status(
    user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
) -> Payload:
    _require_superuser(current_user)
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
    _require_superuser(current_user)
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
    _authorize_credential_action(current_user, auth_repository, user_id)

    # LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- an admin-set password is a
    # temporary one: policy-checked, the user must change it at next sign-in,
    # and the user's existing sessions end now (password_changed_at).
    target = auth_repository.find_user_by_id(user_id)
    try:
        validate_password_policy(
            payload.new_password,
            username=target.username if target else None,
            email=target.email if target else None,
        )
    except PasswordPolicyError as error:
        raise HTTPException(status_code=422, detail=str(error))

    auth_repository.update_password_hash(
        user_id,
        hash_password(payload.new_password),
        updated_by=current_user.user_id,
        must_change_password=True,
        password_changed_at=datetime.now(timezone.utc).replace(microsecond=0),
    )
    # Never echo the new password (or its hash) back, per Hard Rule 24.
    return {"id": user_id, "status": "password_reset", "must_change_password": True}


@router.post("/api/admin/users/{user_id}/set-password-link")
def send_set_password_link(
    user_id: str,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Payload:
    """LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- (re)send the user a
    set-password email (same token store and endpoint as Forgot Password).
    The admin never sees or sets a password through this route."""
    _authorize_credential_action(current_user, auth_repository, user_id)
    sent = password_reset_service.send_set_password_link(user_id)
    return {"id": user_id, "status": "set_password_link_sent" if sent else "set_password_link_not_sent"}


def _authorize_credential_action(current_user, auth_repository, user_id: str) -> None:
    _require_superuser(current_user)
    membership = auth_repository.find_active_membership_for_user(user_id)
    if membership is not None:
        _require_same_organization(current_user, membership.organization_id)
        try:
            authorize_user_management(current_user.role, membership.role)
        except DelegationDeniedError as error:
            raise HTTPException(status_code=403, detail=str(error))


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


# AI5R-WHATSAPP-SENDER-STATUS-001 -- read-only lookup for the Sender
# Access admin screen. Same admin.users gate and organization-boundary
# check as register/activate above; never mutates, never returns the
# raw phone number, never returns the full hash for an ACTIVE identity
# (see get_whatsapp_identity_status's own docstring for why a PENDING
# identity's hash IS returned -- the existing activate endpoint above
# already requires it).
@router.get("/api/admin/users/{user_id}/whatsapp/status")
def get_whatsapp_number_status(
    user_id: str,
    current_user=Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    whatsapp_repository=Depends(get_whatsapp_intake_repository),
) -> Payload:
    _require_admin_users(current_user)
    _require_same_organization_as_target(current_user, auth_repository, user_id)
    try:
        result = get_whatsapp_identity_status(
            target_user_id=user_id,
            auth_repository=auth_repository,
            whatsapp_repository=whatsapp_repository,
        )
    except TargetUserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"data": result}
