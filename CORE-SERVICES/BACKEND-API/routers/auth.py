from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from API.auth_service import AuthenticatedIdentity, AuthenticationError, authenticate
from API.password_reset_service import InvalidTokenError, PasswordResetService, RateLimitExceededError
import dataclasses
from dependencies import (
    get_auth_repository,
    get_current_user,
    get_password_reset_service,
    get_record_change_history_repository,
)
from models.requests import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UpdateProfileEmailRequest,
)
from models.responses import Payload

router = APIRouter()


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

