"""LTSA_POWER_BI_R1B -- governed read-only BI API, contract ltsa-bi/1.0.0.

Router only: every table comes unchanged from BiDatasetService (which
delegates all business rules to the canonical LTSA contracts). All routes
require the dedicated bi.read permission. Errors use the BI error envelope
{success:false, error_code, message, contract_version} -- including 401/403
raised by the auth dependencies -- and never carry SQL, credentials, stack
traces or internal paths. This router is scoped: other APIs keep FastAPI's
default error shape.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from API.auth_service import AuthenticatedIdentity
from API.bi_dataset_service import CONTRACT_VERSION, BiDatasetService, BiError
from dependencies import get_bi_dataset_service, require_permission

logger = logging.getLogger(__name__)

BI_PERMISSION = "bi.read"
_AUTH_ERRORS = {
    401: ("BI_UNAUTHENTICATED", "Authentication required"),
    403: ("BI_FORBIDDEN", f"Missing permission: {BI_PERMISSION}"),
}


def bi_error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error_code": error_code, "message": message, "contract_version": CONTRACT_VERSION},
    )


class _BiRoute(APIRoute):
    """Maps HTTPExceptions raised while resolving dependencies (401/403 from
    auth) to the BI error envelope, for this router only."""

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def bi_handler(request: Request):
            try:
                return await handler(request)
            except HTTPException as error:
                code, message = _AUTH_ERRORS.get(error.status_code, ("BI_INTERNAL_ERROR", "Request failed"))
                return bi_error(error.status_code, code, message)

        return bi_handler


router = APIRouter(prefix="/api/ltsa/bi/v1", tags=["bi"], route_class=_BiRoute)


def _serve(build: Callable[[], dict[str, Any]]) -> Any:
    try:
        return build()
    except BiError as error:
        return bi_error(error.status_code, error.error_code, str(error))
    except Exception:  # noqa: BLE001 -- logged server-side; the client gets no internals
        logger.exception("BI endpoint failed")
        return bi_error(500, "BI_INTERNAL_ERROR", "Internal error while building the BI dataset")


_READ = Depends(require_permission(BI_PERMISSION))
_SERVICE = Depends(get_bi_dataset_service)


@router.get("/metadata")
def get_bi_metadata(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.metadata)


@router.get("/assets")
def get_bi_assets(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.assets)


@router.get("/areas")
def get_bi_areas(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.areas)


@router.get("/cm")
def get_bi_cm(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.cm)


@router.get("/pm")
def get_bi_pm(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.pm)


@router.get("/installations")
def get_bi_installations(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.installations)


@router.get("/mtbf-intervals")
def get_bi_mtbf_intervals(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.mtbf_intervals)


@router.get("/pump-current")
def get_bi_pump_current(_: AuthenticatedIdentity = _READ, service: BiDatasetService = _SERVICE):
    return _serve(service.pump_current)
