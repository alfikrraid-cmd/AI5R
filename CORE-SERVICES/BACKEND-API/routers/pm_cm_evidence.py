from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from API.auth_service import AuthenticatedIdentity, resolve_area_scope
from API.pump_area_scope import is_area_in_scope, resolve_asset_area
from dependencies import (
    get_condition_monitoring_reading_gateway,
    get_current_user,
    get_pm_cm_evidence_repository,
    get_pm_occurrence_gateway,
    get_pump_gateway,
    require_permission,
)
from API.pm_cm_evidence_repository import FileTooLargeError, UnsupportedContentTypeError
from models.responses import Payload

# MWO-LTSA-PM-CM-INTAKE-001 -- evidence attachments for PM Occurrence /
# Condition Monitoring Reading. Gated on maintenance.write (upload) and
# maintenance.read (list/download) -- the same permissions the PM/CMON
# records themselves use, not a new capability invented for evidence.
router = APIRouter()


# MWO-LTSA-AUTH-DATA-SCOPE-FINAL-CLOSURE-001 -- pm_cm_evidence carries
# neither asset_code nor area, only (record_type, record_code) pointing
# at the owning pm_occurrence/condition_monitoring_reading row. Area is
# resolved via a real 2-hop join: record_type/record_code -> the owning
# record's own asset_code (via the SAME gateway list/detail already used
# elsewhere in this app) -> pump_gateway.get_pump(asset_code) -> area
# (API.pump_area_scope.resolve_asset_area). An unrecognized record_type,
# or a record that cannot be resolved, returns None -- fail-closed for a
# scoped Pertamina identity (never guessed, per this MWO's own "if
# ownership cannot be deterministically resolved: fail closed" rule).
_EVIDENCE_ASSET_RESOLVERS = {
    "PM_OCCURRENCE": lambda gateway, code: gateway.get_pm_occurrence(code),
    "CONDITION_MONITORING_READING": lambda gateway, code: gateway.get_condition_monitoring_reading(code),
}


def _resolve_evidence_area(
    record_type: str,
    record_code: str,
    *,
    pm_occurrence_gateway,
    condition_monitoring_reading_gateway,
    pump_gateway,
) -> str | None:
    resolver = _EVIDENCE_ASSET_RESOLVERS.get(record_type)
    if resolver is None:
        return None
    owning_gateway = (
        pm_occurrence_gateway if record_type == "PM_OCCURRENCE" else condition_monitoring_reading_gateway
    )
    try:
        response = resolver(owning_gateway, record_code)
    except Exception:
        return None
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        return None
    return resolve_asset_area(data.get("asset_code"), pump_gateway)


@router.post("/api/ltsa/pm-cm-evidence", dependencies=[Depends(require_permission("maintenance.write"))])
async def upload_pm_cm_evidence(
    record_type: str = Form(...),
    record_code: str = Form(...),
    category: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(require_permission("maintenance.write")),
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
) -> Payload:
    file_bytes = await file.read()
    try:
        created = pm_cm_evidence_repository.create(
            record_type=record_type,
            record_code=record_code,
            file_name=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            category=category,
            source="MANUAL",
            uploaded_by=current_user.user_id,
        )
    except (UnsupportedContentTypeError, FileTooLargeError) as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"data": created}


@router.get("/api/ltsa/pm-cm-evidence", dependencies=[Depends(require_permission("maintenance.read"))])
def list_pm_cm_evidence(
    record_type: str,
    record_code: str,
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
) -> Payload:
    scope = resolve_area_scope(current_user)
    if scope is not None:
        area = _resolve_evidence_area(
            record_type, record_code,
            pm_occurrence_gateway=pm_occurrence_gateway,
            condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
            pump_gateway=pump_gateway,
        )
        if not is_area_in_scope(area, scope):
            return {"data": []}
    return {"data": pm_cm_evidence_repository.list_for_record(record_type, record_code)}


@router.get(
    "/api/ltsa/pm-cm-evidence/{evidence_id}/download",
    dependencies=[Depends(require_permission("maintenance.read"))],
)
def download_pm_cm_evidence(
    evidence_id: str,
    pm_cm_evidence_repository=Depends(get_pm_cm_evidence_repository),
    pm_occurrence_gateway=Depends(get_pm_occurrence_gateway),
    condition_monitoring_reading_gateway=Depends(get_condition_monitoring_reading_gateway),
    pump_gateway=Depends(get_pump_gateway),
    current_user: AuthenticatedIdentity = Depends(get_current_user),
):
    record = pm_cm_evidence_repository.get_file_data(evidence_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such evidence item")

    scope = resolve_area_scope(current_user)
    if scope is not None:
        area = _resolve_evidence_area(
            record["record_type"], record["record_code"],
            pm_occurrence_gateway=pm_occurrence_gateway,
            condition_monitoring_reading_gateway=condition_monitoring_reading_gateway,
            pump_gateway=pump_gateway,
        )
        if not is_area_in_scope(area, scope):
            # Same "No such evidence item" shape as a genuine miss --
            # never a distinct status that would confirm existence.
            raise HTTPException(status_code=404, detail="No such evidence item")

    file_bytes = base64.b64decode(record["file_data_base64"])
    return Response(content=file_bytes, media_type=record["content_type"])
