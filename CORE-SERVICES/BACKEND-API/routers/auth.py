from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from API.auth_service import AuthenticatedIdentity, AuthenticationError, authenticate
from API.password_reset_service import InvalidTokenError, PasswordResetService, RateLimitExceededError
from dependencies import get_auth_repository, get_current_user, get_password_reset_service
from models.requests import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest
from models.responses import Payload

router = APIRouter()


def _identity_payload(identity: AuthenticatedIdentity) -> dict:
    # password_hash is never read here at all (AuthenticatedIdentity has
    # no such field -- resolve_identity()/authenticate() never copy it
    # out of UserRecord), so there is no field to accidentally serialize.
    return {
        "user": {"id": identity.user_id, "username": identity.username, "email": identity.email},
        "organization": {"id": identity.organization_id, "code": identity.organization_code},
        "role": identity.role,
        "permissions": sorted(identity.permissions),
    }


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

