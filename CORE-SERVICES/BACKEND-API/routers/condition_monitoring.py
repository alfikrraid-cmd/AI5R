from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.condition_monitoring_excel_template import build_condition_monitoring_import_template
from API.pm_schedule_excel_import import ExcelImportError, parse_xlsx_grid
from API.pump_area_scope import filter_records_by_asset_scope, is_asset_in_scope
from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_condition_monitoring_reading_repository,
    get_condition_monitoring_schedule_repository,
    get_current_user,
    get_pump_gateway,
    require_permission,
)
from models.requests import (
    AdminReturnForCorrectionRequest,
    BatchCodesRequest,
    BatchTechnicalReviewRequest,
    ConditionMonitoringReadingAdHocBulkCreateRequest,
    ConditionMonitoringReadingAdHocCreateRequest,
    ConditionMonitoringReadingCreateRequest,
    ConditionMonitoringReadingUpdateRequest,
    TechnicalReviewRequest,
    ConditionMonitoringScheduleCreateRequest,
    ConditionMonitoringScheduleUpdateRequest,
)
from models.responses import Payload

# MWO-LTSA-AUTH-001
router = APIRouter(dependencies=[Depends(require_permission("condition.read"))])


@router.post("/api/ltsa/condition-monitoring-schedules", dependencies=[Depends(require_permission("maintenance.write"))])
def create_condition_monitoring_schedule(payload: ConditionMonitoringScheduleCreateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    created = repository.create(values=payload.model_dump(), actor=current_user.user_id)
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump not found")
    return {"data": created}


@router.patch("/api/ltsa/condition-monitoring-schedules/{code}", dependencies=[Depends(require_permission("maintenance.write"))])
def update_condition_monitoring_schedule(code: str, payload: ConditionMonitoringScheduleUpdateRequest, current_user=Depends(require_permission("maintenance.write")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    updated = repository.update(code, values=payload.model_dump(exclude_unset=True), actor=current_user.user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return {"data": updated}


@router.delete("/api/ltsa/condition-monitoring-schedules/{code}", dependencies=[Depends(require_permission("admin.superuser"))])
def delete_condition_monitoring_schedule(code: str, current_user=Depends(require_permission("admin.superuser")), repository=Depends(get_condition_monitoring_schedule_repository)) -> Payload:
    deleted = repository.soft_delete(code, actor=current_user.user_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return {"data": deleted}

# Condition Monitoring API (WO-CMON-002, per ADR-CONDITION-MONITORING-001)
# -- same ConditionMonitoringScheduleGateway/ConditionMonitoringReadingGateway
# built under WO-CMON-001, exposed under the /api/ltsa prefix already used
# by the dashboard's other real LTSA calls (ai5rClient.js). No new
# gateway, service, or repository layer -- mirrors WO-BE-001/WO-PUMP-001/
# WO-MH-001/WO-PM-002/WO-CM-002's identical addition for Work Order/Pump/
# Maintenance History/PM Schedule/CM Report. Only list/detail are exposed
# here for both entities, matching this MWO's scope (ADR-CONDITION-
# MONITORING-001's Future MWOs item 2) -- create/update/delete routes
# were not requested, and the Reading gateway has no update/delete
# methods to expose in the first place (append-only, per WO-CMON-001).
#
# Deliberately independent of routers/cm_report.py -- no shared route
# prefix, no shared gateway, no cross-import, per ADR-CONDITION-
# MONITORING-001's Reason section.


@router.get("/api/ltsa/condition-monitoring-schedules")
def list_ltsa_condition_monitoring_schedules(
    condition_monitoring_schedule_repository=Depends(get_condition_monitoring_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return condition_monitoring_schedule_repository.list_condition_monitoring_schedules(
        scope=resolve_area_scope(current_user)
    )


@router.get("/api/ltsa/condition-monitoring-schedules/{code}")
def get_ltsa_condition_monitoring_schedule(
    code: str,
    condition_monitoring_schedule_repository=Depends(get_condition_monitoring_schedule_repository),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    response = condition_monitoring_schedule_repository.get_condition_monitoring_schedule(
        code, scope=resolve_area_scope(current_user)
    )
    if response.get("data") is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring schedule not found")
    return response


@router.get("/api/ltsa/condition-monitoring-readings")
def list_ltsa_condition_monitoring_readings(
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    return condition_monitoring_reading_repository.list_all(
        scope=resolve_area_scope(current_user), limit=limit, offset=offset
    )


@router.get("/api/ltsa/condition-monitoring-readings/{code}")
def get_ltsa_condition_monitoring_reading(
    code: str,
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    data = condition_monitoring_reading_repository.find_by_code(code)
    scope = resolve_area_scope(current_user)
    if data is None or (scope is not None and not is_asset_in_scope(data.get("asset_code"), scope, pump_gateway)):
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"success": True, "message": "found", "data": data}


# MWO-LTSA-PM-CM-INTAKE-001 -- real draft/submit/review write surface for
# Condition Monitoring Reading. Bypasses ConditionMonitoringReadingGateway/
# n8n entirely (append-only per WO-CMON-001, same reasoning as
# pm_occurrence's own write routes) -- the two GET routes above are
# untouched. Deliberately gated on maintenance.write/maintenance.
# admin_review/maintenance.technical_review, the same permissions PM
# Occurrence uses, not a new condition.write string -- every role that
# needs to reach this domain already holds both maintenance.* and
# condition.read together (confirmed by reading the real ROLE_PERMISSIONS
# matrix before choosing this), so reusing them is the smallest correct
# capability, not a new one invented to fit this router.
def _actor_id(current_user) -> str:
    return current_user.user_id


@router.post(
    "/api/ltsa/condition-monitoring-readings",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_ltsa_condition_monitoring_reading(
    payload: ConditionMonitoringReadingCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    created = condition_monitoring_reading_repository.create_draft(
        condition_monitoring_schedule_code=payload.condition_monitoring_schedule_code,
        asset_code=payload.asset_code,
        asset_type=payload.asset_type,
        reading_date=payload.reading_date,
        measurements=payload.measurements.model_dump(),
        created_by=_actor_id(current_user),
    )
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump or Condition Monitoring schedule not found")
    return {"data": created}


# MWO-LTSA-CMON-ADHOC-ENTRY-001 -- exposes the pre-existing, already-
# proven-in-production ConditionMonitoringReadingRepository.
# create_ad_hoc_draft() over HTTP for the first time. That method has
# shipped every WhatsApp-sourced reading to date via a direct Python
# call; this route changes nothing about it, it only adds a second
# caller. provenance is hardcoded 'MANUAL' (never client-supplied) so a
# web-entered reading is never mistaken for a WhatsApp one, and
# source_reference is server-synthesized (a fresh UUID) since a manual
# web entry has no external message/document to point back to -- the
# repository method requires a real string, and this is never confused
# with a genuine external reference. Reading code, workflow_status, and
# created_by/updated_by are entirely repository-controlled, exactly like
# every other create path in this router; the request body has no way to
# set any of them.
@router.post(
    "/api/ltsa/condition-monitoring-readings/ad-hoc",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_ad_hoc_ltsa_condition_monitoring_reading(
    payload: ConditionMonitoringReadingAdHocCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    created = condition_monitoring_reading_repository.create_ad_hoc_draft(
        asset_code=payload.asset_code,
        asset_type=payload.asset_type,
        reading_date=payload.reading_date,
        measurements=payload.measurements.model_dump(),
        created_by=_actor_id(current_user),
        source_reference=f"MANUAL_WEB:{uuid.uuid4()}",
        finding=payload.finding,
        provenance="MANUAL",
    )
    if created is None:
        raise HTTPException(status_code=404, detail="Canonical pump not found")
    return {"data": created}


# MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- the atomic multi-row sibling of
# the single ad-hoc route above. Every row's provenance/schedule
# sentinel/actor is exactly as server-controlled as the single-row path
# (never per-row client input); the only new server-generated value per
# row is its own reading code and its own source_reference (never
# reused across rows, so two rows in the same batch can never collide
# on the ad-hoc idempotency key). Structural/measurement-schema
# validation is Pydantic's (ConditionMonitoringReadingAdHocCreateRequest,
# reused per-row, never a second row schema); canonical pump existence
# is re-verified inside the repository's own atomic SQL, never trusted
# from the client. create_ad_hoc_batch() either creates every row (and
# its CREATE audit row) or none -- see that method's own docstring for
# the exact all-or-nothing mechanism.
@router.post(
    "/api/ltsa/condition-monitoring-readings/ad-hoc/bulk",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def create_ad_hoc_ltsa_condition_monitoring_readings_bulk(
    payload: ConditionMonitoringReadingAdHocBulkCreateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    rows = [
        {
            "asset_code": reading.asset_code,
            "asset_type": reading.asset_type,
            "reading_date": reading.reading_date,
            "measurements": reading.measurements.model_dump(),
            "finding": reading.finding,
            "source_reference": f"MANUAL_WEB:{uuid.uuid4()}",
        }
        for reading in payload.readings
    ]
    try:
        created = condition_monitoring_reading_repository.create_ad_hoc_batch(rows, created_by=actor)
    except Exception as error:  # noqa: BLE001 -- DB driver exception type varies; means the repository's own DO block raised and Postgres rolled everything back
        raise HTTPException(status_code=409, detail=str(error))
    if len(created) != len(rows):
        raise HTTPException(status_code=409, detail="bulk ad-hoc reading creation did not complete atomically")
    return {"data": created}


# MWO-LTSA-CMON-EXCEL-IMPORT-001 -- Excel import is DECODE-ONLY, exactly
# PM4E's own established architecture (parse_pm_schedule_excel, routers/
# pm_schedule.py): this route never resolves a pump, never validates a
# measurement, and never writes to condition_monitoring_reading,
# condition_monitoring_schedule, pm_occurrence, or pm_schedule -- it
# turns bytes into a JSON {headers, rows} grid and nothing else. Every
# business rule (header aliasing, pump resolution, numeric/leak parsing)
# lives client-side (utils/conditionMonitoringExcelImport.js) against
# the SAME canonical pump list and measurement catalog the Bulk Editor
# already loads. parse_xlsx_grid() is reused directly from PM4E's own
# module -- it is domain-neutral (headers/rows only, no PM knowledge at
# all), so importing it here creates no CMON-depends-on-PM-business-
# logic coupling. Gated by maintenance.write for the same reason as the
# PM route: this endpoint's only legitimate use is as the first step of
# a create flow.
@router.post(
    "/api/ltsa/condition-monitoring-readings/import/parse",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
async def parse_condition_monitoring_excel(
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


# A static, non-user-influenced .xlsx generated fresh on every request.
@router.get(
    "/api/ltsa/condition-monitoring-readings/import/template",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def download_condition_monitoring_import_template(
    current_user=Depends(require_permission("maintenance.write")),
) -> Response:
    content = build_condition_monitoring_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="condition_monitoring_import_template.xlsx"'},
    )


@router.patch(
    "/api/ltsa/condition-monitoring-readings/{code}",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def update_ltsa_condition_monitoring_reading_draft(
    code: str,
    payload: ConditionMonitoringReadingUpdateRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    updated = condition_monitoring_reading_repository.update_draft(
        code,
        reading_date=payload.reading_date,
        measurements=payload.measurements.model_dump(),
        finding=payload.finding,
        updated_by=_actor_id(current_user),
    )
    if updated is None:
        raise HTTPException(
            status_code=409, detail="Condition Monitoring reading not found or not editable in its current state"
        )
    return {"data": updated}


@router.delete(
    "/api/ltsa/condition-monitoring-readings/{code}",
    dependencies=[Depends(require_permission("admin.superuser"))],
)
def delete_ltsa_condition_monitoring_reading(
    code: str,
    current_user=Depends(require_permission("admin.superuser")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    deleted = condition_monitoring_reading_repository.soft_delete(code, deleted_by=_actor_id(current_user))
    if deleted is None:
        raise HTTPException(status_code=404, detail="Condition Monitoring reading not found")
    return {"data": deleted}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/submit",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def submit_ltsa_condition_monitoring_reading(
    code: str,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    submitted = condition_monitoring_reading_repository.submit(code, submitted_by=_actor_id(current_user))
    if submitted is None:
        raise HTTPException(
            status_code=409, detail="Condition Monitoring reading not found or not submittable in its current state"
        )
    return {"data": submitted}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/admin-review",
    dependencies=[Depends(require_permission("maintenance.admin_review"))],
)
def admin_review_ltsa_condition_monitoring_reading(
    code: str,
    payload: AdminReturnForCorrectionRequest,
    current_user=Depends(require_permission("maintenance.admin_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    returned = condition_monitoring_reading_repository.admin_return_for_correction(
        code, reviewed_by=_actor_id(current_user), return_reason=payload.return_reason
    )
    if returned is None:
        raise HTTPException(status_code=409, detail="Condition Monitoring reading not found or not in SUBMITTED state")
    return {"data": returned}


@router.post(
    "/api/ltsa/condition-monitoring-readings/{code}/technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def technical_review_ltsa_condition_monitoring_reading(
    code: str,
    payload: TechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    if payload.action == "RETURN":
        result = condition_monitoring_reading_repository.technical_return_for_correction(
            code, technical_reviewed_by=actor, technical_comment=payload.comment
        )
    else:
        outcome = "ACKNOWLEDGED" if payload.action == "ACKNOWLEDGE" else "TECHNICALLY_APPROVED"
        result = condition_monitoring_reading_repository.technical_finalize(
            code,
            technical_reviewed_by=actor,
            technical_outcome=outcome,
            technical_comment=payload.comment,
            technical_recommendation=payload.recommendation,
        )
    if result is None:
        raise HTTPException(status_code=409, detail="Condition Monitoring reading not found or not in SUBMITTED state")
    return {"data": result}


# MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-019 -- see pm_occurrence.py's
# own identical batch routes for the full reasoning: thin per-record
# orchestration around the SAME condition_monitoring_reading_repository
# methods the individual routes above already call.
@router.post(
    "/api/ltsa/condition-monitoring-readings/batch-submit",
    dependencies=[Depends(require_permission("maintenance.write"))],
)
def batch_submit_ltsa_condition_monitoring_readings(
    payload: BatchCodesRequest,
    current_user=Depends(require_permission("maintenance.write")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
            result = condition_monitoring_reading_repository.submit(code, submitted_by=actor)
        except Exception as exc:  # noqa: BLE001
            failed.append({"code": code, "reason": str(exc)})
            continue
        if result is None:
            skipped.append({"code": code, "reason": "not found or not in a submittable state"})
        else:
            succeeded.append(code)
    return {"data": {"succeeded": succeeded, "skipped": skipped, "failed": failed}}


@router.post(
    "/api/ltsa/condition-monitoring-readings/batch-technical-review",
    dependencies=[Depends(require_permission("maintenance.technical_review"))],
)
def batch_technical_review_ltsa_condition_monitoring_readings(
    payload: BatchTechnicalReviewRequest,
    current_user=Depends(require_permission("maintenance.technical_review")),
    condition_monitoring_reading_repository=Depends(get_condition_monitoring_reading_repository),
) -> Payload:
    actor = _actor_id(current_user)
    succeeded: list[str] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for code in payload.codes:
        try:
            if payload.action == "RETURN":
                result = condition_monitoring_reading_repository.technical_return_for_correction(
                    code, technical_reviewed_by=actor, technical_comment=payload.comment
                )
            else:
                outcome = "ACKNOWLEDGED" if payload.action == "ACKNOWLEDGE" else "TECHNICALLY_APPROVED"
                result = condition_monitoring_reading_repository.technical_finalize(
                    code,
                    technical_reviewed_by=actor,
                    technical_outcome=outcome,
                    technical_comment=payload.comment,
                    technical_recommendation=payload.recommendation,
                )
        except Exception as exc:  # noqa: BLE001
            failed.append({"code": code, "reason": str(exc)})
            continue
        if result is None:
            skipped.append({"code": code, "reason": "not found or not in SUBMITTED state"})
        else:
            succeeded.append(code)
    return {"data": {"succeeded": succeeded, "skipped": skipped, "failed": failed}}
