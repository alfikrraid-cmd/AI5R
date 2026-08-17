from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies import get_installation_gateway, require_permission
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("drawing.read"))])

# Installation Report API (MWO-LTSA-060, production persistence path for
# the Installation Workspace created by MWO-LTSA-056) -- reuses
# InstallationGateway unmodified, exposed under the /api/ltsa prefix
# already used by every other LTSA registry endpoint (mirrors
# pm_schedule.py's list/detail pair exactly). List and detail only,
# matching InstallationGateway's own real capability -- create/update/
# delete are out of this MWO's scope.


@router.get("/api/ltsa/installations")
def list_ltsa_installations(installation_gateway=Depends(get_installation_gateway)) -> Payload:
    return installation_gateway.list_installations()


@router.get("/api/ltsa/installations/{installation_code}")
def get_ltsa_installation(
    installation_code: str, installation_gateway=Depends(get_installation_gateway)
) -> Payload:
    return installation_gateway.get_installation(installation_code)
