from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.operational_registry_repository import BulkPMScheduleValidationError
from API.pm_schedule_excel_import import ExcelImportError, parse_xlsx_grid
from API.pm_schedule_excel_template import build_pm_schedule_import_template
from dependencies import get_current_user, get_pm_schedule_repository, require_permission
from models.requests import PMScheduleBulkCreateRequest, PMScheduleCreateRequest, PMScheduleUpdateRequest
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("maintenance.read"))])


def _actor_id(user: AuthenticatedIdentity) -> str:
    return user.user_id


@router.post("/api/ltsa/pm-schedules", dependencies=[Depends(require_permission("maintenance.write"))])
def create_pm_schedule(payload: PMScheduleCreateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    created = repository.create(values=payload.model_dump(), actor=_actor_id(current_user))
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump not found")
    return {"data": created}


# AI5R-PHASE4E3, Section I -- ONE atomic backend bulk endpoint, gated by
# the same maintenance.write permission as the single-create route above
# (Section K: reuse, never widen). Registered as a literal "/bulk" path
# segment, distinct from the "/{code}" PATCH/DELETE routes below -- no
# path-matching ambiguity since no other POST exists at "/{code}".
@router.post("/api/ltsa/pm-schedules/bulk", dependencies=[Depends(require_permission("maintenance.write"))])
def bulk_create_pm_schedules(
    payload: PMScheduleBulkCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    repository=Depends(get_pm_schedule_repository),
) -> Payload:
    try:
        created = repository.bulk_create(
            rows=[row.model_dump() for row in payload.rows],
            actor=_actor_id(current_user),
        )
    except BulkPMScheduleValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"client_row_id": row_id, "msg": message} for row_id, message in exc.row_errors.items()],
        ) from exc
    return {"data": created}


# AI5R-PHASE4E4, Section B/C/K -- Excel import is DECODE-ONLY: this route
# never resolves a pump, never validates a frequency/date/activity, and
# never touches pm_schedule/pm_occurrence -- it turns bytes into a JSON
# grid and nothing else. All of that logic lives client-side
# (utils/pmExcelImport.js) against the SAME canonical pump list the
# manual bulk editor already loads. Gated by maintenance.write (not
# merely maintenance.read) because this endpoint only has a legitimate
# use as the first step of a create flow -- same reasoning as the "Bulk
# Schedule"/"Import Excel" buttons only being shown to writers.
@router.post("/api/ltsa/pm-schedules/import/parse", dependencies=[Depends(require_permission("maintenance.write"))])
async def parse_pm_schedule_excel(
    file: UploadFile = File(...),
    current_user=Depends(require_permission("maintenance.write")),
) -> Payload:
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Only .xlsx files are supported.")

    contents = await file.read()
    try:
        grid = parse_xlsx_grid(contents)
    except ExcelImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": grid}


# Section D/O -- a static, non-user-influenced .xlsx generated fresh on
# every request (no caching of a stale template if the column set ever
# changes). No permission beyond maintenance.read is needed to READ a
# blank template, but restricted to maintenance.write anyway since only
# a writer has any use for it (mirrors the parse route's own reasoning).
@router.get("/api/ltsa/pm-schedules/import/template", dependencies=[Depends(require_permission("maintenance.write"))])
def download_pm_schedule_import_template(
    current_user=Depends(require_permission("maintenance.write")),
) -> Response:
    content = build_pm_schedule_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="pm_schedule_import_template.xlsx"'},
    )


@router.patch("/api/ltsa/pm-schedules/{code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_pm_schedule(code: str, payload: PMScheduleUpdateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    updated = repository.update(code, values=payload.model_dump(exclude_unset=True), actor=_actor_id(current_user))
    if updated is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return {"data": updated}


@router.delete("/api/ltsa/pm-schedules/{code}", dependencies=[Depends(require_permission("admin.superuser"))])
def delete_pm_schedule(code: str, current_user=Depends(require_permission("admin.superuser")), repository=Depends(get_pm_schedule_repository)) -> Payload:
    deleted = repository.soft_delete(code, actor=_actor_id(current_user))
    if deleted is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return {"data": deleted}

# PM Schedule Registry API (WO-PM-002, per ADR-PM-001) -- same
# PMScheduleGateway built under WO-PM-001, exposed under the /api/ltsa
# prefix already used by the dashboard's other real LTSA calls
# (ai5rClient.js). No new gateway, service, or repository layer -- mirrors
# WO-BE-001/WO-PUMP-001/WO-MH-001's identical addition for Work Order/
# Pump/Maintenance History. Only list/detail are exposed here, matching
# this MWO's scope -- create/update/delete routes were not requested.
#
# MWO-LTSA-AUTH-DATA-SCOPE-ROUTE-CLOSURE-001 -- pm_schedule carries
# asset_code, never area; scope resolved via pump_gateway.get_pump()
# (API.pump_area_scope), same 1-hop join as every other asset_code
# domain in this closure.


@router.get("/api/ltsa/pm-schedules")
def list_ltsa_pm_schedules(
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return pm_schedule_repository.list_pm_schedules(scope=resolve_area_scope(current_user))


@router.get("/api/ltsa/pm-schedules/{code}")
def get_ltsa_pm_schedule(
    code: str,
    pm_schedule_repository=Depends(get_pm_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = pm_schedule_repository.get_pm_schedule(code, scope=resolve_area_scope(current_user))
    if response.get("data") is None:
        raise HTTPException(status_code=404, detail="PM schedule not found")
    return response
