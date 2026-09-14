from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Depends, HTTPException, Query

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.ltsa_contract_coverage_service import ContractNotFound, InvalidReportingPeriod
from dependencies import get_current_user, get_ltsa_contract_coverage_service, get_ltsa_contract_repository, require_permission
from models.responses import Payload

# MWO-LTSA-CONTRACT-SCOPE-R3 -- READ API foundation only (Chief Architect
# approved design, R2/R3). No write routes exist yet: contract/scope
# bootstrap is a separate, later, human-reviewed mission (R4) -- see this
# router's own header discipline in ltsa_contract_repository.py. Reuses
# "condition.read" (not a new permission string) -- Contract Coverage is
# presented as part of the Condition Monitoring domain per the mission's
# own UI target (R2 Section 8), and every role that already reaches
# Condition Monitoring already holds this permission.
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])


@router.get("/api/ltsa/contracts")
def list_contracts(
    repository=Depends(get_ltsa_contract_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    # Contracts are not themselves area-scoped (a contract's own assets
    # may legitimately span multiple MAs) -- Area/MA data scope is
    # enforced on the per-asset endpoints below instead, the same point
    # every other cross-area aggregate in this codebase enforces it
    # (routers/fleet.py's own scope=resolve_area_scope(current_user)
    # passed into build(), not applied to a list of contracts).
    return {"success": True, "data": repository.list_contracts()}


@router.get("/api/ltsa/contracts/{contract_code}/assets")
def get_contract_assets(
    contract_code: str,
    period_start: str = Query(..., description="Reporting period start, ISO date (YYYY-MM-DD)."),
    period_end: str = Query(..., description="Reporting period end, ISO date (YYYY-MM-DD)."),
    coverage_service=Depends(get_ltsa_contract_coverage_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    try:
        rows = coverage_service.list_assets(
            contract_code, period_start, period_end, scope=resolve_area_scope(current_user)
        )
    except ContractNotFound:
        raise HTTPException(status_code=404, detail="Contract not found")
    except InvalidReportingPeriod as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"success": True, "data": [dataclasses.asdict(row) for row in rows]}


@router.get("/api/ltsa/contracts/{contract_code}/coverage")
def get_contract_coverage(
    contract_code: str,
    period_start: str = Query(..., description="Reporting period start, ISO date (YYYY-MM-DD)."),
    period_end: str = Query(..., description="Reporting period end, ISO date (YYYY-MM-DD)."),
    coverage_service=Depends(get_ltsa_contract_coverage_service),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    try:
        coverage = coverage_service.build_coverage(
            contract_code, period_start, period_end, scope=resolve_area_scope(current_user)
        )
    except ContractNotFound:
        raise HTTPException(status_code=404, detail="Contract not found")
    except InvalidReportingPeriod as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"success": True, "data": dataclasses.asdict(coverage)}
