from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from API.auth_service import AuthenticatedIdentity, AuthenticationError, authenticate
from dependencies import get_auth_repository, get_current_user
from models.requests import LoginRequest
from models.responses import Payload

router = APIRouter()


def _identity_payload(identity: AuthenticatedIdentity) -> dict:
    # password_hash is never read here at all (AuthenticatedIdentity has
    # no such field -- resolve_identity()/authenticate() never copy it
    # out of UserRecord), so there is no field to accidentally serialize.
    return {
        "user": {"id": identity.user_id, "email": identity.email},
        "organization": {"id": identity.organization_id, "code": identity.organization_code},
        "role": identity.role,
        "permissions": sorted(identity.permissions),
    }


@router.post("/api/auth/login")
def login(payload: LoginRequest, auth_repository=Depends(get_auth_repository)) -> Payload:
    try:
        token, identity = authenticate(auth_repository, payload.email, payload.password)
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
