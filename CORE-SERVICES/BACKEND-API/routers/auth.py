from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from API.auth_password import PasswordPolicyError, hash_password, validate_password_policy, verify_password
from API.auth_service import AuthenticatedIdentity, AuthenticationError, authenticate, issue_access_token
from API.password_reset_service import (
    FailedPasswordAttemptLimiter,
    InvalidTokenError,
    PasswordResetService,
    RateLimitExceededError,
)
import dataclasses
from dependencies import (
    get_auth_repository,
    get_change_password_attempt_limiter,
    get_current_user,
    get_password_reset_service,
    get_record_change_history_repository,
)
from models.requests import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UpdateProfileEmailRequest,
)
from models.responses import Payload

router = APIRouter()
logger = logging.getLogger("auth.change_password")


def _identity_payload(identity: AuthenticatedIdentity) -> dict:
    # password_hash is never read here at all (AuthenticatedIdentity has
    # no such field -- resolve_identity()/authenticate() never copy it
    # out of UserRecord), so there is no field to accidentally serialize.
    org_name = getattr(identity, "organization_name", None) or identity.organization_code
    return {
        "id": identity.user_id,
        "name": identity.name,
        "username": identity.username,
        "email": identity.email,
        "user": {
            "id": identity.user_id,
            "username": identity.username,
            "name": identity.name,
            "email": identity.email,
        },
        "organization": {
            "id": identity.organization_id,
            "code": identity.organization_code,
            "name": org_name,
        },
        "role": identity.role,
        "permissions": sorted(identity.permissions),
        "data_scope_type": identity.data_scope_type,
        "data_scope_value": identity.data_scope_value,
        "must_change_password": bool(getattr(identity, "must_change_password", False)),
    }


def _normalize_and_validate_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if not cleaned:
        raise HTTPException(status_code=422, detail="Email cannot be empty")
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise HTTPException(status_code=422, detail="Invalid email format")
    parts = cleaned.split("@")
    if (
        len(parts) != 2
        or not parts[0]
        or not parts[1]
        or "." not in parts[1]
        or parts[1].startswith(".")
        or parts[1].endswith(".")
    ):
        raise HTTPException(status_code=422, detail="Invalid email format")
    return cleaned


@router.post("/api/auth/login")
def login(payload: LoginRequest, auth_repository=Depends(get_auth_repository)) -> Payload:
    try:
        identifier = payload.identifier or payload.email
        if not identifier:
            raise AuthenticationError("Invalid username/email or password")
        token, identity = authenticate(auth_repository, identifier, payload.password)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error))

    return {
        "access_token": token,
        "token_type": "bearer",
        **_identity_payload(identity),
    }


@router.get("/api/auth/me")
def me(current_user: AuthenticatedIdentity = Depends(get_current_user)) -> Payload:
    return _identity_payload(current_user)


@router.patch("/api/auth/me")
def update_me(
    payload: UpdateProfileEmailRequest,
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    history_repository=Depends(get_record_change_history_repository),
) -> Payload:
    normalized_email = _normalize_and_validate_email(payload.email)

    existing = auth_repository.find_user_by_email(normalized_email)
    if existing is not None and existing.id != current_user.user_id:
        raise HTTPException(status_code=409, detail="Email already registered to another user")

    # If same normalized email already belongs to current user, return 200 without DB update
    if current_user.email and current_user.email.lower() == normalized_email:
        return _identity_payload(current_user)

    old_email = current_user.email
    auth_repository.update_user_email(current_user.user_id, normalized_email, updated_by=current_user.user_id)

    if history_repository is not None:
        try:
            history_repository.append(
                entity_type="user",
                entity_id=current_user.user_id,
                field_name="email",
                old_value="[REDACTED]" if old_email else None,
                new_value="[REDACTED]",
                changed_by=current_user.user_id,
                reason="self_service_email_update",
            )
        except Exception:
            pass

    updated_identity = dataclasses.replace(current_user, email=normalized_email)
    return _identity_payload(updated_identity)


@router.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: AuthenticatedIdentity = Depends(get_current_user),
    auth_repository=Depends(get_auth_repository),
    attempt_limiter: FailedPasswordAttemptLimiter = Depends(get_change_password_attempt_limiter),
) -> Payload:
    """LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- self-service change, also the
    only way out of a forced first-login change. A wrong current password is
    400, never 401: the dashboard signs the user out on any 401."""
    user_id = current_user.user_id
    if attempt_limiter.is_blocked(user_id):
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please try again later.")

    user = auth_repository.find_user_by_id(user_id)
    if user is None or not verify_password(payload.current_password, user.password_hash):
        attempt_limiter.record_failure(user_id)
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    try:
        validate_password_policy(payload.new_password, username=user.username, email=user.email)
    except PasswordPolicyError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=422, detail="New password must be different from the current password")

    # Whole seconds: the fresh token below is issued at exactly this instant,
    # and resolve_identity rejects only tokens with an earlier iat.
    changed_at = datetime.now(timezone.utc).replace(microsecond=0)
    changed = auth_repository.change_password(
        user_id,
        expected_password_hash=user.password_hash,
        new_password_hash=hash_password(payload.new_password),
        password_changed_at=changed_at,
        reason="self_service_password_change",
    )
    if not changed:
        raise HTTPException(status_code=409, detail="Password was changed by another request. Please sign in again.")

    attempt_limiter.clear(user_id)
    logger.info("password_changed user_id=%s", user_id)
    token = issue_access_token(user_id, current_user.organization_id, issued_at=changed_at)
    identity = dataclasses.replace(current_user, must_change_password=False)
    return {"access_token": token, "token_type": "bearer", **_identity_payload(identity)}


@router.post("/api/auth/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Payload:
    client_ip = request.client.host if request.client else "unknown"
    try:
        password_reset_service.request_password_reset(payload.identifier, client_ip=client_ip)
    except RateLimitExceededError as error:
        raise HTTPException(status_code=429, detail=str(error))

    return {"message": "If the account is eligible, password reset instructions have been sent."}


@router.post("/api/auth/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Payload:
    client_ip = request.client.host if request.client else "unknown"
    try:
        password_reset_service.reset_password(payload.token, payload.new_password, client_ip=client_ip)
    except InvalidTokenError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    return {"message": "Password has been successfully reset. Please log in with your new password."}

