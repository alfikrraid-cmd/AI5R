from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.ltsa_finding_repository import (
    AssetMismatch,
    ClosedRequiresClosedDate,
    InvalidSourceDomain,
    LtsaFindingRepository,
    SourceRecordNotFound,
)
from API.pump_area_scope import is_area_in_scope
from dependencies import get_current_user, get_ltsa_finding_repository, require_permission
from models.responses import Payload

# MWO-LTSA-REPORTING-R4-1 -- wired into the real DI surface
# (dependencies.get_ltsa_finding_repository, dependencies._ltsa_finding_
# repository) and registered in main.py, now that both files are clean
# again. The self-contained local DI this router used in R4 (while
# dependencies.py/main.py were concurrently dirty) is retired -- no
# duplicate repository instance remains.


# Router-level "condition.read" (not a new permission string) -- Findings
# are presented as part of the Condition Monitoring / reporting domain
# (per LTSA_REPORTING_R2_DATA_FOUNDATION's own read-model design) and
# every role that already reaches Condition Monitoring already holds
# this permission, same reasoning as routers/ltsa_contract.py. Write
# routes are additionally gated on "maintenance.write", the same
# permission PM Occurrence/Condition Monitoring Reading writes already
# use -- not a new "finding.write" string invented for this router.
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])


def _actor_id(current_user: AuthenticatedIdentity) -> str:
    return current_user.user_id


class LtsaFindingCreateRequest(BaseModel):
    source_domain: str
    source_record_code: str
    asset_code: str | None = None
    finding_text: str
    status: str | None = None
    severity: str | None = None
    recommendation: str | None = None
    action: str | None = None
    owner_pic: str | None = None
    opened_date: str | None = None
    closed_date: str | None = None
    source_reference: str | None = None


class LtsaFindingUpdateRequest(BaseModel):
    finding_text: str | None = None
    status: str | None = None
    severity: str | None = None
    recommendation: str | None = None
    action: str | None = None
    owner_pic: str | None = None
    opened_date: str | None = None
    closed_date: str | None = None


@router.get("/api/ltsa/findings")
def list_ltsa_findings(
    source_domain: str | None = Query(None),
    source_record_code: str | None = Query(None),
    asset_code: str | None = Query(None),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    opened_after: str | None = Query(None),
    opened_before: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: LtsaFindingRepository = Depends(get_ltsa_finding_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return repository.list_findings(
        source_domain=source_domain,
        source_record_code=source_record_code,
        asset_code=asset_code,
        status=status,
        severity=severity,
        opened_after=opened_after,
        opened_before=opened_before,
        scope=resolve_area_scope(current_user),
        limit=limit,
        offset=offset,
    )


@router.get("/api/ltsa/findings/{finding_code}")
def get_ltsa_finding(
    finding_code: str,
    repository: LtsaFindingRepository = Depends(get_ltsa_finding_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    data = repository.find_by_code_with_area(finding_code)
    if data is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    scope = resolve_area_scope(current_user)
    if not is_area_in_scope(data.pop("asset_area", None), scope):
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"success": True, "data": data}


@router.post("/api/ltsa/findings", dependencies=[Depends(require_permission("maintenance.write"))])
def create_ltsa_finding(
    payload: LtsaFindingCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: LtsaFindingRepository = Depends(get_ltsa_finding_repository),
) -> Payload:
    try:
        created = repository.create(
            source_domain=payload.source_domain,
            source_record_code=payload.source_record_code,
            asset_code=payload.asset_code,
            finding_text=payload.finding_text,
            status=payload.status,
            severity=payload.severity,
            recommendation=payload.recommendation,
            action=payload.action,
            owner_pic=payload.owner_pic,
            opened_date=payload.opened_date,
            closed_date=payload.closed_date,
            source_reference=payload.source_reference,
            created_by=_actor_id(current_user),
        )
    except InvalidSourceDomain as exc:
        raise HTTPException(status_code=400, detail=f"Invalid source_domain: {exc}")
    except SourceRecordNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Source record not found: {exc}")
    except AssetMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ClosedRequiresClosedDate as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True, "data": created}


@router.patch("/api/ltsa/findings/{finding_code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_ltsa_finding(
    finding_code: str,
    payload: LtsaFindingUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository: LtsaFindingRepository = Depends(get_ltsa_finding_repository),
) -> Payload:
    try:
        updated = repository.update(
            finding_code,
            values=payload.model_dump(exclude_unset=True),
            updated_by=_actor_id(current_user),
        )
    except ClosedRequiresClosedDate as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if updated is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"success": True, "data": updated}
